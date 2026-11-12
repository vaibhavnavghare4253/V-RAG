from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUserDep, DbDep
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import Organization, User, UserRole
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: DbDep,
) -> Any:
    """Register a new user and organization workspace."""
    # Check if user already exists
    stmt = select(User).where(User.email == user_in.email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # Create Organization
    org = Organization(
        name=user_in.organization_name or f"{user_in.email.split('@')[0]}'s Workspace",
        tier="standard",
    )
    db.add(org)
    await db.flush()

    # Create User (First user in new org is ADMIN)
    new_user = User(
        organization_id=org.id,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Load organization relation for UserRead schema
    stmt_user = select(User).where(User.id == new_user.id).options(selectinload(User.organization))
    user_with_org = (await db.execute(stmt_user)).scalar_one()

    # Create token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user_with_org.id,
        expires_delta=access_token_expires,
        extra_claims={"org_id": user_with_org.organization_id, "role": user_with_org.role.value},
    )

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user_with_org),
    )


@router.post("/login", response_model=Token)
async def login_for_access_token(
    db: DbDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """OAuth2 password login to obtain access token."""
    stmt = select(User).where(User.email == form_data.username).options(selectinload(User.organization))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        extra_claims={"org_id": user.organization_id, "role": user.role.value},
    )

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: CurrentUserDep,
) -> Any:
    """Retrieve details of the currently authenticated user."""
    return current_user

