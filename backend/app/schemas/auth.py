import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MAX_LENGTH = 1024


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class LoginInput(InputModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class ChangePasswordInput(InputModel):
    current_password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=10, max_length=PASSWORD_MAX_LENGTH)


class UserCreate(InputModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: str
    temporary_password: str = Field(min_length=10, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("display_name")
    @classmethod
    def display_name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display name must not be blank")
        return value


class UserUpdate(InputModel):
    email: EmailStr | None = None
    display_name: str | None = Field(None, min_length=1, max_length=120)
    role: str | None = None
    is_active: bool | None = None

    @field_validator("email", "display_name", "role", "is_active")
    @classmethod
    def required_fields_cannot_be_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @field_validator("display_name")
    @classmethod
    def updated_display_name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Display name must not be blank")
        return value


class PasswordReset(InputModel):
    temporary_password: str = Field(min_length=10, max_length=PASSWORD_MAX_LENGTH)


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
