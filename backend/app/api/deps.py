from typing import Annotated, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.retrieval.embedder import BaseEmbedder, get_embedder
from app.schemas.user import TokenPayload
from app.services.rag_service import BaselineTextRAGService
from app.services.storage import StorageService, get_storage_service
from app.services.vector_store import VectorStoreService, get_vector_store

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_db_session_factory():
    return AsyncSessionLocal


def get_rag_service(
    embedder: Annotated[BaseEmbedder, Depends(get_embedder)],
    vector_store: Annotated[VectorStoreService, Depends(get_vector_store)],
) -> BaselineTextRAGService:
    return BaselineTextRAGService(embedder=embedder, vector_store=vector_store)


DbDep = Annotated[AsyncSession, Depends(get_db)]
SessionFactoryDep = Annotated[object, Depends(get_db_session_factory)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]
StorageDep = Annotated[StorageService, Depends(get_storage_service)]
EmbedderDep = Annotated[BaseEmbedder, Depends(get_embedder)]
VectorStoreDep = Annotated[VectorStoreService, Depends(get_vector_store)]
RAGServiceDep = Annotated[BaselineTextRAGService, Depends(get_rag_service)]


async def get_current_user(
    db: DbDep,
    token: TokenDep,
) -> User:
    """Validate bearer token and retrieve the authenticated user with tenant context."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return user


async def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the authenticated user has administrative permissions."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have administrative privileges",
        )
    return current_user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
AdminUserDep = Annotated[User, Depends(get_current_active_admin)]

