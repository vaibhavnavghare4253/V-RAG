from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CitationRead(BaseModel):
    document_id: str
    document_name: str
    page_number: int
    asset_id: Optional[str] = None
    asset_type: Optional[str] = None  # "text", "table", "chart", "figure"
    bounding_box: Optional[Dict[str, float]] = None
    snippet: str


class QueryRequest(BaseModel):
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    query: str = Field(..., min_length=2, max_length=2000)
    stream: bool = False


class QueryResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    decision: str  # "ANSWER", "ABSTAIN"
    uncertainty_score: float
    citations: List[CitationRead]
    latency_ms: int
    diagnostics: Optional[Dict[str, Any]] = None


class MessageRead(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    decision: Optional[str] = None
    uncertainty_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    document_id: Optional[str] = None
    title: Optional[str] = "New Conversation"


class ConversationRead(BaseModel):
    id: str
    user_id: str
    document_id: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
