import secrets
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from apps.backoffice.models import StaffUser
from core.db.session import get_db
from core.lib.authentication import (
    AUTHENTICATION_EXCEPTION,
    decode_token,
    verify_password,
    pwd_context
)
from core.lib.exceptions import BadRequest
from core.lib.permissions import oauth2_scheme


def get_staff_user(db: Session, username: str):
    user = db.query(StaffUser).filter(StaffUser.username == username).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    return user


def authenticate_staff_user(db: Session, username: str, password: str):
    user = get_staff_user(db, username)
    if not verify_password(password, user.password):
        user.login_attempt += 1
        if user.login_attempt >= 5:
            user.status = "Password Locked"
        db.commit()
        raise BadRequest(
            exception_type="user.invalid_credentials",
            msg="Invalid username or password",
        )
    user.login_attempt = 0
    db.commit()
    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
    payload, scopes = decode_token(token)
    if payload is None:
        raise AUTHENTICATION_EXCEPTION
    username: str | None = payload.get("sub")
    if username is None:
        raise AUTHENTICATION_EXCEPTION
    user = None
    if "Staff" in payload.get("scopes", []):
        user = get_staff_user(db, username)
    if user is None:
        raise AUTHENTICATION_EXCEPTION
    return user, scopes


def generate_hash(plain_text):
    return pwd_context.hash(plain_text)


def generate_password_reset_token():
    return secrets.token_urlsafe(30)