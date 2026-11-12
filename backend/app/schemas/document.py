from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.document import AssetType, DocumentStatus, JobStatus


class IngestionJobRead(BaseModel):
    id: str
    document_id: str
    status: JobStatus
    current_stage: int
    total_stages: int
    stage_name: str
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentAssetRead(BaseModel):
    id: str
    document_id: str
    page_id: Optional[str] = None
    asset_type: AssetType
    bounding_box: Optional[Dict[str, Any]] = None
    storage_path: Optional[str] = None
    extracted_content: Optional[str] = None
    visual_description: Optional[str] = None
    asset_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentRead(BaseModel):
    id: str
    organization_id: str
    filename: str
    file_size_bytes: int
    page_count: int
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailRead(DocumentRead):
    file_hash_sha256: str
    doc_metadata: Optional[Dict[str, Any]] = None
    latest_job: Optional[IngestionJobRead] = None
    asset_counts: Optional[Dict[str, int]] = None

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    document_id: str
    job_id: str
    filename: str
    file_size_bytes: int
    status: DocumentStatus
    message: str = "Document uploaded successfully and queued for processing"


class PaginatedDocuments(BaseModel):
    items: List[DocumentRead]
    total: int
    page: int
    limit: int
    total_pages: int
