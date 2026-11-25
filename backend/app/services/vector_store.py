from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.core.config import settings


@dataclass
class VectorNode:
    """Represents a chunk or asset node to upsert into Qdrant."""

    point_id: str
    vector: List[float]
    tenant_id: str
    document_id: str
    document_name: str
    chunk_id: str
    page_number: int
    modality: str
    content: str
    asset_id: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None


@dataclass
class RetrievedNode:
    """Represents a search hit returned by Qdrant."""

    point_id: str
    score: float
    document_id: str
    document_name: str
    chunk_id: str
    page_number: int
    modality: str
    content: str
    asset_id: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None


class VectorStoreService:
    """Qdrant vector database wrapper with mandatory tenant isolation filtering."""

    def __init__(self, client: Optional[QdrantClient] = None, collection_name: Optional[str] = None):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        if client is not None:
            self.client = client
        elif settings.QDRANT_MODE == "memory":
            self.client = QdrantClient(":memory:")
        elif settings.QDRANT_MODE == "local":
            local_path = Path(settings.QDRANT_LOCAL_PATH)
            local_path.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(local_path))
        else:
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                api_key=settings.QDRANT_API_KEY,
            )

    def ensure_collection(self, dimension: int) -> None:
        """Create the Qdrant collection and payload indexes if they do not exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            for field_name, schema in [
                ("tenant_id", PayloadSchemaType.KEYWORD),
                ("document_id", PayloadSchemaType.KEYWORD),
                ("modality", PayloadSchemaType.KEYWORD),
                ("page_number", PayloadSchemaType.INTEGER),
            ]:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=schema,
                    )
                except Exception:
                    # In-memory Qdrant may ignore explicit payload schema calls
                    pass

    def upsert_nodes(self, nodes: List[VectorNode], dimension: int) -> None:
        """Upsert a batch of vector nodes into Qdrant."""
        if not nodes:
            return
        self.ensure_collection(dimension)
        points = [
            PointStruct(
                id=node.point_id,
                vector=node.vector,
                payload={
                    "tenant_id": node.tenant_id,
                    "document_id": node.document_id,
                    "document_name": node.document_name,
                    "chunk_id": node.chunk_id,
                    "page_number": node.page_number,
                    "modality": node.modality,
                    "content": node.content,
                    "asset_id": node.asset_id,
                    "bounding_box": node.bounding_box,
                },
            )
            for node in nodes
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self,
        query_vector: List[float],
        tenant_id: str,
        document_id: Optional[str] = None,
        modalities: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[RetrievedNode]:
        """Execute a tenant-isolated vector similarity search."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            return []

        must_conditions: List[FieldCondition] = [
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
        ]
        if document_id:
            must_conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=document_id))
            )
        if modalities:
            must_conditions.append(
                FieldCondition(key="modality", match=MatchAny(any=modalities))
            )

        query_filter = Filter(must=must_conditions)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        results: List[RetrievedNode] = []
        for hit in response.points:
            payload = hit.payload or {}
            results.append(
                RetrievedNode(
                    point_id=str(hit.id),
                    score=float(hit.score),
                    document_id=str(payload.get("document_id", "")),
                    document_name=str(payload.get("document_name", "Unknown")),
                    chunk_id=str(payload.get("chunk_id", "")),
                    page_number=int(payload.get("page_number", 1)),
                    modality=str(payload.get("modality", "text")),
                    content=str(payload.get("content", "")),
                    asset_id=payload.get("asset_id"),
                    bounding_box=payload.get("bounding_box"),
                )
            )
        return results

    def delete_by_document(self, document_id: str, tenant_id: str) -> None:
        """Remove all indexed points belonging to a specific document and tenant."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                    FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                ]
            ),
        )


_cached_vector_store: Optional[VectorStoreService] = None


def get_vector_store() -> VectorStoreService:
    """Dependency / factory returning the singleton VectorStoreService."""
    global _cached_vector_store
    if _cached_vector_store is None:
        _cached_vector_store = VectorStoreService()
    return _cached_vector_store

