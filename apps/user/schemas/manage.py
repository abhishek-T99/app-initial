from datetime import datetime
from pydantic import EmailStr
from uuid import UUID

from core.lib.pydantic import Schema


class UserReadSchema(Schema):
    id: UUID
    name: str
    email: EmailStr
    password: str | None = None
    profile_picture: str | None = None
    phone_number: str
    is_active: bool
    last_login: datetime | None = None
    is_locked: bool


class UserListSchema(Schema):
    id: UUID
    name: str
    email: EmailStr | None
    phone_number: str
    is_active: bool
    last_login: datetime | None = None
    is_locked: bool


class UserMinimalListSchema(Schema):
    phone_number: str
    value: str


class ValidateResetTokenSchema(Schema):
    token: str

    class Config:
        schema_extra = {
            "example": {
                "token": "LbBsXDysj7wjO3prllQ4IfMk0zNGEVqJbPkJj6l6",
            }
        }


class UserUpdateSchema(Schema):
    name: str | None = None
    email: EmailStr | None = None
    id_number: str | None = None


class UserLoginSessionRecord(Schema):
    phone_number: str
    updated_at: datetime
    name: str
