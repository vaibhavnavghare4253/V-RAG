import hashlib
import math
from typing import Any, Optional
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import (
    CurrentUserDep,
    DbDep,
    EmbedderDep,
    SessionFactoryDep,
    StorageDep,
    VectorStoreDep,
)
from app.core.config import settings
from app.ingestion.pipeline import run_text_ingestion_pipeline
from app.models.base import generate_uuid
from app.models.document import Document, DocumentStatus, IngestionJob, JobStatus
from app.schemas.document import (
    DocumentDetailRead,
    DocumentRead,
    DocumentUploadResponse,
    IngestionJobRead,
    PaginatedDocuments,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    db: DbDep,
    session_factory: SessionFactoryDep,
    storage: StorageDep,
    vector_store: VectorStoreDep,
    embedder: EmbedderDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
) -> Any:
    """Upload a PDF document to be indexed for multimodal RAG."""
    # 1. Validate file extension and MIME type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF files are supported.",
        )

    # 2. Read contents and validate size
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_mb}MB.",
        )
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 3. Compute SHA256 hash for deduplication check
    file_hash = hashlib.sha256(contents).hexdigest()

    # 4. Check for existing identical document in this tenant
    stmt_existing = select(Document).where(
        Document.organization_id == current_user.organization_id,
        Document.file_hash_sha256 == file_hash,
    )
    existing_doc = (await db.execute(stmt_existing)).scalar_one_or_none()
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An identical document '{existing_doc.filename}' already exists in your workspace.",
        )

    # 5. Persist original file via StorageService
    doc_id = generate_uuid()
    storage_relative_path = f"documents/{current_user.organization_id}/{doc_id}.pdf"
    await storage.save_file(
        file_bytes=contents,
        relative_path=storage_relative_path,
        content_type="application/pdf",
    )

    # 6. Create Database Records (Document & IngestionJob)
    document = Document(
        id=doc_id,
        organization_id=current_user.organization_id,
        uploaded_by=current_user.id,
        filename=file.filename,
        file_size_bytes=file_size,
        file_hash_sha256=file_hash,
        storage_path=storage_relative_path,
        status=DocumentStatus.PENDING,
    )
    db.add(document)

    job_id = generate_uuid()
    job = IngestionJob(
        id=job_id,
        document_id=doc_id,
        status=JobStatus.PENDING,
        current_stage=0,
        total_stages=6,
        stage_name="Uploaded and queued",
    )
    db.add(job)

    await db.commit()

    background_tasks.add_task(
        run_text_ingestion_pipeline,
        document_id=doc_id,
        job_id=job_id,
        session_factory=session_factory,
        storage=storage,
        vector_store=vector_store,
        embedder=embedder,
    )

    return DocumentUploadResponse(
        document_id=doc_id,
        job_id=job_id,
        filename=file.filename,
        file_size_bytes=file_size,
        status=DocumentStatus.PENDING,
        message="Document successfully uploaded and queued for processing.",
    )


@router.get("", response_model=PaginatedDocuments)
async def list_documents(
    db: DbDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[DocumentStatus] = Query(None, alias="status"),
) -> Any:
    """List all documents for the current tenant workspace with pagination."""
    query = select(Document).where(Document.organization_id == current_user.organization_id)
    if status_filter:
        query = query.where(Document.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Apply pagination and sorting
    offset = (page - 1) * limit
    paged_query = query.order_by(desc(Document.created_at)).offset(offset).limit(limit)
    items = (await db.execute(paged_query)).scalars().all()

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedDocuments(
        items=[DocumentRead.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{document_id}", response_model=DocumentDetailRead)
async def get_document(
    document_id: str,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Any:
    """Retrieve details for a specific document."""
    stmt = (
        select(Document)
        .where(
            Document.id == document_id,
            Document.organization_id == current_user.organization_id,
        )
        .options(selectinload(Document.ingestion_jobs))
    )
    document = (await db.execute(stmt)).scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    # Get latest ingestion job if present
    latest_job = None
    if document.ingestion_jobs:
        sorted_jobs = sorted(document.ingestion_jobs, key=lambda j: j.created_at, reverse=True)
        latest_job = IngestionJobRead.model_validate(sorted_jobs[0])

    detail = DocumentDetailRead(
        id=document.id,
        organization_id=document.organization_id,
        filename=document.filename,
        file_size_bytes=document.file_size_bytes,
        file_hash_sha256=document.file_hash_sha256,
        page_count=document.page_count,
        status=document.status,
        error_message=document.error_message,
        doc_metadata=document.doc_metadata,
        created_at=document.created_at,
        updated_at=document.updated_at,
        latest_job=latest_job,
    )
    return detail


@router.get("/{document_id}/status", response_model=IngestionJobRead)
async def get_document_status(
    document_id: str,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Any:
    """Poll the status of the current ingestion job for a document."""
    # Verify tenant ownership
    stmt_doc = select(Document.id).where(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
    )
    exists = (await db.execute(stmt_doc)).scalar_one_or_none()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    stmt_job = (
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(desc(IngestionJob.created_at))
        .limit(1)
    )
    job = (await db.execute(stmt_job)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ingestion job found for this document.",
        )

    return IngestionJobRead.model_validate(job)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: DbDep,
    storage: StorageDep,
    vector_store: VectorStoreDep,
    current_user: CurrentUserDep,
) -> None:
    """Delete a document, its stored files, and all associated extracted assets."""
    stmt = select(Document).where(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
    )
    document = (await db.execute(stmt)).scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    # Delete vectors from Qdrant
    vector_store.delete_by_document(document_id=document_id, tenant_id=current_user.organization_id)

    # Delete original file from storage
    if document.storage_path:
        await storage.delete_file(document.storage_path)

    # Delete database record (cascades to pages, assets, chunks, and jobs)
    await db.delete(document)
    await db.commit()

