from dataclasses import dataclass
import time
from typing import List, Optional

from app.generation.llm_provider import BaseLLMProvider, get_llm_provider
from app.generation.prompt_templates import BASELINE_A_SYSTEM_PROMPT, build_rag_user_prompt
from app.retrieval.embedder import BaseEmbedder, get_embedder
from app.schemas.chat import CitationRead
from app.services.vector_store import RetrievedNode, VectorStoreService, get_vector_store


@dataclass
class RAGQueryResult:
    """Result of executing a RAG query pipeline."""

    answer: str
    decision: str
    uncertainty_score: float
    citations: List[CitationRead]
    retrieved_nodes: List[RetrievedNode]
    latency_ms: int
    total_tokens: int
    model: str


class BaselineTextRAGService:
    """Baseline A: Standard Text-Only RAG.

    Retrieves top-K text chunks via dense vector similarity and generates a grounded
    answer with page-level citations. Always answers (no calibrated abstention).
    """

    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional[VectorStoreService] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.embedder = embedder or get_embedder()
        self.vector_store = vector_store or get_vector_store()
        self.llm_provider = llm_provider or get_llm_provider()

    async def query(
        self,
        query_text: str,
        tenant_id: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
    ) -> RAGQueryResult:
        start_time = time.perf_counter()

        # 1. Embed query
        query_vector = await self.embedder.embed_query(query_text)

        # 2. Retrieve top-K text chunks scoped to tenant (and optional document)
        nodes = self.vector_store.search(
            query_vector=query_vector,
            tenant_id=tenant_id,
            document_id=document_id,
            modalities=["text"],
            top_k=top_k,
        )

        # 3. Generate grounded answer
        user_prompt = build_rag_user_prompt(query_text, nodes)
        llm_resp = await self.llm_provider.generate(
            system_prompt=BASELINE_A_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # 4. Build citations
        citations = [
            CitationRead(
                document_id=node.document_id,
                document_name=node.document_name,
                page_number=node.page_number,
                asset_id=node.asset_id,
                asset_type=node.modality,
                bounding_box=node.bounding_box,
                snippet=node.content[:300] + ("..." if len(node.content) > 300 else ""),
            )
            for node in nodes
        ]

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        # Baseline A does not perform calibrated uncertainty estimation; store raw 1 - top_score proxy
        top_score = max((n.score for n in nodes), default=0.0)
        naive_uncertainty = round(max(0.0, min(1.0, 1.0 - top_score)), 4)

        return RAGQueryResult(
            answer=llm_resp.content,
            decision="ANSWER",
            uncertainty_score=naive_uncertainty,
            citations=citations,
            retrieved_nodes=nodes,
            latency_ms=elapsed_ms,
            total_tokens=llm_resp.prompt_tokens + llm_resp.completion_tokens,
            model=llm_resp.model,
        )

