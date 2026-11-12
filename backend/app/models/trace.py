from typing import Any, Dict, List, Optional
from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class RetrievalTrace(Base, TimestampMixin):
    __tablename__ = "retrieval_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    intent_category: Mapped[str] = mapped_column(String(50), nullable=False)
    selected_modalities: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    iteration_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    candidate_nodes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    rerank_scores: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    uncertainty_breakdown: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="trace")


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    baseline_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

