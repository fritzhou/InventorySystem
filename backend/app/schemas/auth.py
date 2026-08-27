import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: str
    temporary_password: str = Field(min_length=10)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(None, min_length=1, max_length=120)
    role: str | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    temporary_password: str = Field(min_length=10)


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_email: str | None
    actor_display_name: str | None
    action: str
    entity_type: str
    entity_id: str | None
    event_metadata: dict | None
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEventRead]
    total: int
    page: int
    page_size: int
