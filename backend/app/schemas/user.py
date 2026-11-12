from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    tier: str = Field(default="standard")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationRead(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.MEMBER


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    organization_name: Optional[str] = Field(default="Default Workspace")


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    is_active: bool
    created_at: datetime
    organization: Optional[OrganizationRead] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenPayload(BaseModel):
    sub: str
    org_id: Optional[str] = None
    exp: Optional[int] = None
