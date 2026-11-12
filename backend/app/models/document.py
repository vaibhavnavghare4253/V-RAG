import enum
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class AssetType(str, enum.Enum):
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    FIGURE = "figure"
    DIAGRAM = "diagram"
    PAGE = "page"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="documents")
    uploader: Mapped[Optional["User"]] = relationship("User", back_populates="uploaded_documents")
    pages: Mapped[List["DocumentPage"]] = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    assets: Mapped[List["DocumentAsset"]] = relationship("DocumentAsset", back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    ingestion_jobs: Mapped[List["IngestionJob"]] = relationship("IngestionJob", back_populates="document", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base, TimestampMixin):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width_pt: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    height_pt: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rendered_storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    assets: Mapped[List["DocumentAsset"]] = relationship("DocumentAsset", back_populates="page", cascade="all, delete-orphan")


class DocumentAsset(Base, TimestampMixin):
    __tablename__ = "document_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=True)
    
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False, index=True)
    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # [x0, y0, x1, y1]
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    extracted_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asset_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="assets")
    page: Mapped[Optional["DocumentPage"]] = relationship("DocumentPage", back_populates="assets")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="asset")


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("document_assets.id", ondelete="SET NULL"), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qdrant_point_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    asset: Mapped[Optional["DocumentAsset"]] = relationship("DocumentAsset", back_populates="chunks")


class IngestionJob(Base, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    
    current_stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_stages: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), default="Queued", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    started_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="ingestion_jobs")
