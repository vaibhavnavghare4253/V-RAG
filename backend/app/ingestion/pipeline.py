from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.ingestion.chunker import chunk_pages
from app.ingestion.text_extractor import extract_text_from_pdf
from app.models.base import generate_uuid
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentStatus,
    IngestionJob,
    JobStatus,
)
from app.retrieval.embedder import BaseEmbedder, get_embedder
from app.services.storage import StorageService, get_storage_service
from app.services.vector_store import VectorNode, VectorStoreService, get_vector_store


async def _update_job_stage(
    db: AsyncSession,
    job: IngestionJob,
    stage: int,
    stage_name: str,
    status: JobStatus = JobStatus.PROCESSING,
) -> None:
    job.status = status
    job.current_stage = stage
    job.stage_name = stage_name
    await db.commit()


async def run_text_ingestion_pipeline(
    document_id: str,
    job_id: str,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    storage: Optional[StorageService] = None,
    vector_store: Optional[VectorStoreService] = None,
    embedder: Optional[BaseEmbedder] = None,
) -> None:
    """Execute Phase 2 text-only PDF ingestion pipeline: extract -> chunk -> embed -> index."""
    factory = session_factory or AsyncSessionLocal
    storage_svc = storage or get_storage_service()
    vec_store = vector_store or get_vector_store()
    emb = embedder or get_embedder()

    async with factory() as db:
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        job = (await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))).scalar_one_or_none()
        if not doc or not job:
            return

        try:
            job.started_at = datetime.now(timezone.utc).isoformat()
            doc.status = DocumentStatus.PROCESSING
            await _update_job_stage(db, job, 1, "Reading PDF from storage")

            pdf_bytes = await storage_svc.get_file(doc.storage_path)

            await _update_job_stage(db, job, 2, "Extracting page text")
            pages = extract_text_from_pdf(pdf_bytes)
            doc.page_count = len(pages)

            for p in pages:
                db.add(
                    DocumentPage(
                        document_id=doc.id,
                        page_number=p.page_number,
                        width_pt=p.width_pt,
                        height_pt=p.height_pt,
                    )
                )

            await _update_job_stage(db, job, 3, "Chunking text")
            text_chunks = chunk_pages(pages, chunk_size_tokens=512, overlap_tokens=64)

            await _update_job_stage(db, job, 4, "Generating dense embeddings")
            vectors = await emb.embed_texts([c.content for c in text_chunks]) if text_chunks else []

            await _update_job_stage(db, job, 5, "Indexing vectors in Qdrant")
            vector_nodes = []
            for chunk, vec in zip(text_chunks, vectors):
                chunk_id = generate_uuid()
                point_id = generate_uuid()
                db.add(
                    DocumentChunk(
                        id=chunk_id,
                        document_id=doc.id,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        qdrant_point_id=point_id,
                    )
                )
                vector_nodes.append(
                    VectorNode(
                        point_id=point_id,
                        vector=vec,
                        tenant_id=doc.organization_id,
                        document_id=doc.id,
                        document_name=doc.filename,
                        chunk_id=chunk_id,
                        page_number=chunk.page_number,
                        modality="text",
                        content=chunk.content,
                    )
                )

            if vector_nodes:
                vec_store.upsert_nodes(vector_nodes, dimension=emb.dimension)

            doc.status = DocumentStatus.INDEXED
            job.completed_at = datetime.now(timezone.utc).isoformat()
            await _update_job_stage(db, job, 6, "Completed", status=JobStatus.COMPLETED)

        except Exception as exc:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(exc)
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            await db.commit()

