from typing import Any, List
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, select

from app.api.deps import CurrentUserDep, DbDep, RAGServiceDep
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.trace import RetrievalTrace
from app.schemas.chat import ConversationCreate, ConversationRead, MessageRead, QueryRequest, QueryResponse

router = APIRouter(prefix="/chat", tags=["Chat & Q&A"])


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conv_in: ConversationCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Any:
    """Create a new chat conversation thread for a document or global workspace."""
    if conv_in.document_id:
        stmt_doc = select(Document.id).where(
            Document.id == conv_in.document_id,
            Document.organization_id == current_user.organization_id,
        )
        if not (await db.execute(stmt_doc)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied.",
            )

    conv = Conversation(
        user_id=current_user.id,
        document_id=conv_in.document_id,
        title=conv_in.title or "New Conversation",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations", response_model=List[ConversationRead])
async def list_conversations(
    db: DbDep,
    current_user: CurrentUserDep,
) -> Any:
    """List all active conversations for the authenticated user."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.updated_at))
    )
    conversations = (await db.execute(stmt)).scalars().all()
    return conversations


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageRead])
async def list_messages(
    conversation_id: str,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Any:
    """Fetch message history for a conversation."""
    stmt_conv = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    )
    conv = (await db.execute(stmt_conv)).scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    stmt_msgs = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = (await db.execute(stmt_msgs)).scalars().all()
    return messages


@router.post("/query", response_model=QueryResponse)
async def submit_query(
    query_in: QueryRequest,
    db: DbDep,
    rag_service: RAGServiceDep,
    current_user: CurrentUserDep,
) -> Any:
    """Execute Baseline A (Standard Text-Only RAG) query with tenant-isolated retrieval."""
    if query_in.document_id:
        stmt_doc = select(Document.id).where(
            Document.id == query_in.document_id,
            Document.organization_id == current_user.organization_id,
        )
        if not (await db.execute(stmt_doc)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied.",
            )

    # Create or retrieve conversation
    conv_id = query_in.conversation_id
    if conv_id:
        stmt_conv = select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.user_id == current_user.id,
        )
        if not (await db.execute(stmt_conv)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied.",
            )
    else:
        conv = Conversation(
            user_id=current_user.id,
            document_id=query_in.document_id,
            title=query_in.query[:50],
        )
        db.add(conv)
        await db.flush()
        conv_id = conv.id

    # Record user message
    user_msg = Message(
        conversation_id=conv_id,
        sender="user",
        content=query_in.query,
    )
    db.add(user_msg)

    # Run Baseline A Text RAG
    rag_result = await rag_service.query(
        query_text=query_in.query,
        tenant_id=current_user.organization_id,
        document_id=query_in.document_id,
        top_k=5,
    )

    citations_payload = [c.model_dump() for c in rag_result.citations]
    assistant_msg = Message(
        conversation_id=conv_id,
        sender="assistant",
        content=rag_result.answer,
        decision=rag_result.decision,
        uncertainty_score=rag_result.uncertainty_score,
        citations=citations_payload,
    )
    db.add(assistant_msg)
    await db.flush()

    # Persist retrieval trace for research evaluation
    trace = RetrievalTrace(
        message_id=assistant_msg.id,
        intent_category="TEXT_BASELINE_A",
        selected_modalities=["text"],
        iteration_count=1,
        candidate_nodes=[
            {
                "chunk_id": n.chunk_id,
                "document_id": n.document_id,
                "page_number": n.page_number,
                "score": round(n.score, 4),
            }
            for n in rag_result.retrieved_nodes
        ],
        rerank_scores=[round(n.score, 4) for n in rag_result.retrieved_nodes],
        uncertainty_breakdown={"naive_1_minus_top_score": rag_result.uncertainty_score},
        latency_ms=rag_result.latency_ms,
        total_tokens=rag_result.total_tokens,
    )
    db.add(trace)
    await db.commit()
    await db.refresh(assistant_msg)

    return QueryResponse(
        conversation_id=conv_id,
        message_id=assistant_msg.id,
        answer=rag_result.answer,
        decision=rag_result.decision,
        uncertainty_score=rag_result.uncertainty_score,
        citations=rag_result.citations,
        latency_ms=rag_result.latency_ms,
        diagnostics={
            "mode": "baseline_a_text_rag",
            "model": rag_result.model,
            "retrieved_count": len(rag_result.retrieved_nodes),
            "total_tokens": rag_result.total_tokens,
        },
    )
