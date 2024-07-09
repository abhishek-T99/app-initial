import re
from datetime import datetime
from pydantic import EmailStr, validator
from uuid import UUID

from core.lib.pydantic import Schema


class UserSchema(Schema):
    name: str
    phone_number: str
    is_active: bool


class PasswordeRetrieveSchema(Schema):
    password: str

    class Config:
        schema_extra = {"example": {"password": "John Doe 123"}}


class PasswordSchema(Schema):
    password: str

    @validator("password")
    def validate_password(cls, v):
        if not re.match(r"^(?=.*[a-zA-Z])(?=.*[0-9])[a-zA-Z0-9\s]{8,20}$", v):
            raise ValueError(
                "Invalid password. It must contain both alphabets "
                "and numbers and should be 8-20 characters long."
            )
        return v

    class Config:
        schema_extra = {"example": {"password": "John Doe 123"}}


class PasswordUpdateSchema(PasswordSchema):
    old_password: str

    class Config:
        schema_extra = {
            "example": {
                "old_password": "John Doe 123",
                "password": "Jane Doe 321",
            }
        }


class PasswordVerifyOTPSchema(Schema):
    otp: str
    otp_reference_number: str

    @validator("otp")
    def validate_otp_length(cls, otp):
        if len(otp) != 6 or not otp.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return otp

    @validator("otp_reference_number")
    def validate_otp_reference_number(cls, otp_reference_number):
        if len(otp_reference_number) < 15:
            raise ValueError("Invalid OTP reference number")
        return otp_reference_number

    class Config:
        schema_extra = {
            "example": {
                "otp": "123456",
                "otp_reference_number": "20230927131649S",
            }
        }


class LoginSchema(Schema):
    phone_number: str

    @validator("phone_number")
    def validate_phone_number(cls, v):
        if v.startswith("60") and bool(re.match(r"^60(?!0)\d{9,10}$", v)) is False:
            raise ValueError("Invalid phone number")
        if bool(re.match(r"^..\d{9,11}$", v)) is False:
            raise ValueError("Invalid phone number")
        return v

    class Config:
        schema_extra = {"example": {"phone_number": "60185549421"}}


class ValidateOTPSchema(Schema):
    otp: str

    class Config:
        schema_extra = {"example": {"otp": "123456"}}


class UserDetailSchema(Schema):
    id: UUID
    name: str
    email: EmailStr | None
    phone_number: str
    is_active: bool
    last_login: datetime | None = None
    is_locked: bool
    profile_picture: str | None = None


class UserUpdateSchema(Schema):
    profile_picture: str | None = None
    name: str

