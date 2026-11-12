from typing import Any, List
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, select

from app.api.deps import CurrentUserDep, DbDep
from app.models.conversation import Conversation, Message
from app.schemas.chat import ConversationCreate, ConversationRead, MessageRead, QueryRequest, QueryResponse

router = APIRouter(prefix="/chat", tags=["Chat & Q&A"])


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conv_in: ConversationCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Any:
    """Create a new chat conversation thread for a document or global workspace."""
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
    current_user: CurrentUserDep,
) -> Any:
    """Adaptive Multimodal Query Endpoint (Foundation scaffold ready for Phase 2-6 engines)."""
    # Create or retrieve conversation
    conv_id = query_in.conversation_id
    if not conv_id:
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

    # Scaffolding response until Phase 2 RAG baseline is attached
    assistant_content = (
        "AdaptiveDocAI Foundation Initialized. Document indexing and RAG baselines "
        "will be attached in Phase 2."
    )
    assistant_msg = Message(
        conversation_id=conv_id,
        sender="assistant",
        content=assistant_content,
        decision="ANSWER",
        uncertainty_score=0.1,
        citations=[],
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return QueryResponse(
        conversation_id=conv_id,
        message_id=assistant_msg.id,
        answer=assistant_content,
        decision="ANSWER",
        uncertainty_score=0.1,
        citations=[],
        latency_ms=12,
        diagnostics={"mode": "foundation_scaffold"},
    )

