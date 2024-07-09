from datetime import datetime
from pydantic import EmailStr, validator
from typing import Literal, List, Tuple, Dict
from uuid import UUID

from apps.backoffice.utils import get_formatted_permissions
from core.lib.pydantic import Schema


class PermissionValidatorBaseSchema(Schema):
    @validator("permissions", check_fields=False)
    def validate_permissions(cls, v):
        return get_formatted_permissions(v)


class PermissionPolicyFormSchema(Schema):
    name: str
    description: str | None = None
    permissions: List[Tuple[str, str]]


class PermissionPolicyUpdateSchema(PermissionPolicyFormSchema):
    is_active: bool


class PermissionPolicyListSchema(Schema):
    id: str
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PermissionPolicyRetrieveSchema(
    PermissionPolicyListSchema, PermissionValidatorBaseSchema
):
    permissions: List[Tuple[str, str]]


class PermissionPolicyBaseSchema(PermissionValidatorBaseSchema):
    id: int
    name: str
    description: str | None = None


class PermissionPolicySchema(PermissionPolicyBaseSchema):
    is_active: bool
    permissions: List[Tuple[str, str]]


class PermissionPolicyInitSchema(Schema):
    data: List[PermissionPolicyBaseSchema]


class UserSchema(Schema):
    id: UUID
    name: str
    force_change_password: bool


class LoginResponse(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserSchema
    permissions: Dict[str, List[str]] | None = {}


class StaffUserReadSchema(Schema):
    id: UUID
    role: str
    name: str
    username: str
    phone_number: str
    status: str
    status_remarks: str | None


class StaffUserFormSchema(Schema):
    role: Literal["Backoffice", "Company"]
    name: str
    username: EmailStr
    phone_number: str
    status: Literal["Active", "Inactive", "Blocked", "Terminated"]
    status_remarks: str | None = None


class ResetPasswordSchema(Schema):
    old_password: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, new_password):
        import re

        pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!#$%&\'()*+,-./:;<=>?@[\]^_`{|}~])(?!.*\s).{8,25}$"
        if not re.match(pattern, new_password):
            raise ValueError("New password must meet the criteria.")
        return new_password

    class Config:
        schema_extra = {
            "example": {"old_password": "asfdQ23@", "new_password": "fsd34Rt#"}
        }


class ForgotPasswordSchema(Schema):
    username: EmailStr


class PasswordChangeSchema(Schema):
    token: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, new_password):
        import re

        pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!#$%&\'()*+,-./:;<=>?@[\]^_`{|}~])(?!.*\s).{8,25}$"
        if not re.match(pattern, new_password):
            raise ValueError("New password must meet the criteria.")
        return new_password

    class Config:
        schema_extra = {
            "example": {
                "token": "LbBsXDysj7wjO3prllQ4IfMk0zNGEVqJbPkJj6l6",
                "new_password": "fsd34Rt!",
            }
        }


class ValidateResetTokenSchema(Schema):
    token: str

    class Config:
        schema_extra = {
            "example": {
                "token": "LbBsXDysj7wjO3prllQ4IfMk0zNGEVqJbPkJj6l6",
            }
        }

