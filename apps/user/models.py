import uuid
from datetime import date, datetime, timedelta
from fastapi import Depends, HTTPException, Request
from sqlalchemy import (
    String,
    false,
    func,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from uuid import UUID
from typing import Literal

from core.config import config
from core.db import Base
from core.db.session import get_db
from core.lib.authentication import create_access_token
from core.redis import cache


class User(Base):
    id: Mapped[UUID] = mapped_column(default=uuid.uuid4, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    email: Mapped[str | None] = mapped_column(String(512))
    password: Mapped[str | None] = mapped_column(String(200))
    profile_picture: Mapped[str | None]
    phone_number: Mapped[str] = mapped_column(String(80), index=True, unique=True)
    is_active: Mapped[bool] = mapped_column(server_default=false())
    is_locked: Mapped[bool] = mapped_column(server_default=false())
    status: Mapped[
        Literal["Inactive", "Blocked", "Whitelisted", "Password Locked"] | None
    ] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(
        index=True, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        index=True,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login: Mapped[datetime | None]
    date_of_birth: Mapped[date | None]
    access_token_id: Mapped[str | None] = mapped_column(String(100), unique=True)

    def create_token(self, db: Session, phone_number=None, expires_delta=None):
        if not expires_delta:
            expires_delta = timedelta(
                minutes=config.auth_token.user_access_token_expiry_minutes
            )

        access_token_id = self.refresh_token(db)

        return create_access_token(
            data={
                "sub": self.name,
                "jti": access_token_id,
                "sid": str(self.id),
                "is_active": self.is_active,
                "mdi": phone_number,
                "udi": self.phone_number,
                "emi": self.email,
            },
            expires_delta=expires_delta,
        )
    
    def refresh_token(self, db: Session):
        self.access_token_id = uuid.uuid4().hex
        db.commit()
        cache.set(f"jti:{self.id}", self.access_token_id)
        return self.access_token_id
    
    @classmethod
    def get(cls, request: Request, db: Session = Depends(get_db)):
        user = None
        if "Staff" not in request.auth.scopes:
            user = (
                db.query(User)
                .filter(User.phone_number == request.user.phone_number)
                .first()
            )
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        return user
    
    @classmethod
    # implement after creating onboarding session table
    def create(cls, onboarding_data):
        pass

    @classmethod
    # implement after creating onboarding session table
    def update(cls, data):
        pass


class UserLoginSession(Base):
    id: Mapped[UUID] = mapped_column(default=uuid.uuid4, primary_key=True, index=True)
    user_id: Mapped[UUID | None]
    otp: Mapped[str | None]
    otp_tries: Mapped[int] = mapped_column(server_default="0")
    phone_number: Mapped[str]
    name: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    otp_verified: Mapped[bool] = mapped_column(server_default=false())
    login_time: Mapped[datetime | None]

    @classmethod
    def fetch_latest(cls, db: Session, user_id: UUID):
        return db.query(cls).filter_by(user_id=user_id).order_by(cls.created_at.desc()).first()


class UserOTP(Base):
    id: Mapped[int] = mapped_column(
        primary_key=True, unique=True, autoincrement=True, index=True
    )
    phone_number: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[UUID | None] = mapped_column(index=True)
    otp_type: Mapped[
        Literal[
            "Password",
            "Login",
            "SignUp",
        ]
    ]
    otp_value: Mapped[str] = mapped_column(String(6))
    otp_reference_number: Mapped[str] = mapped_column(String(16))
    message_body: Mapped[str] = mapped_column(String(2000))
    status: Mapped[Literal["Active", "Inactive", "Pending"] | None] = mapped_column(
        server_default="Pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        index=True, server_default=func.now()
    )


class UserPasswordHistory(Base):
    id: Mapped[int] = mapped_column(
        primary_key=True, unique=True, autoincrement=True, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(index=True)
    old_password: Mapped[str | None] = mapped_column(String(200))
    new_password: Mapped[str | None] = mapped_column(String(200))
    otp_reference_number: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=True
    )
