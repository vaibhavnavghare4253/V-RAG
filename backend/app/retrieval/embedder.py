import abc
import asyncio
import hashlib
import re
from typing import List, Optional
import httpx
import numpy as np

from app.core.config import settings


class BaseEmbedder(abc.ABC):
    """Abstract interface for dense text embedding providers."""

    dimension: int

    @abc.abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate L2-normalized dense vectors for a batch of texts."""
        pass

    async def embed_query(self, text: str) -> List[float]:
        """Generate a dense vector for a single query."""
        vectors = await self.embed_texts([text])
        return vectors[0]


class LocalHashEmbedder(BaseEmbedder):
    """Lightweight deterministic feature-hashing embedder for local dev and testing.

    Projects word unigrams and bigrams into a fixed-dimensional normalized vector space,
    preserving lexical cosine similarity without requiring external APIs or GPU weights.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _embed_single(self, text: str) -> List[float]:
        vec = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            vec[0] = 1.0
            return vec.tolist()

        # Unigrams + bigrams for better phrase matching
        features = list(tokens) + [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
        for feat in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            val = int.from_bytes(digest, "little")
            idx = val % self.dimension
            sign = 1.0 if ((val >> 63) & 1) == 0 else -1.0
            vec[idx] += sign

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]


class SentenceTransformerEmbedder(BaseEmbedder):
    """Local SentenceTransformer embedder (e.g., BAAI/bge-small-en-v1.5)."""

    def __init__(self, model_name: str, dimension: int = 384):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension() or dimension

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        def _encode() -> List[List[float]]:
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()

        return await asyncio.to_thread(_encode)


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI Embeddings API client via httpx."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimension: int = 1536):
        self.api_key = api_key
        self.model = model
        self.dimension = dimension

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"input": texts, "model": self.model},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            data.sort(key=lambda item: item["index"])
            return [item["embedding"] for item in data]


_cached_embedder: Optional[BaseEmbedder] = None


def get_embedder() -> BaseEmbedder:
    """Factory returning the configured dense embedding provider."""
    global _cached_embedder
    if _cached_embedder is not None:
        return _cached_embedder

    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        _cached_embedder = OpenAIEmbedder(
            api_key=settings.OPENAI_API_KEY,
            model=settings.DENSE_EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )
    elif provider == "sentence_transformers":
        _cached_embedder = SentenceTransformerEmbedder(
            model_name=settings.DENSE_EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )
    else:
        _cached_embedder = LocalHashEmbedder(dimension=settings.EMBEDDING_DIMENSION)

    return _cached_embedder

