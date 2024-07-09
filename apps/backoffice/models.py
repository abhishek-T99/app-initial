import uuid
from datetime import datetime
from sqlalchemy import ARRAY, Column, ForeignKey, String, func, or_, true
from sqlalchemy import (
    false,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from typing import Literal, Optional
from uuid import UUID

from core.db import Base
from core.lib.authentication import (
    generate_random_password,
    pwd_context,
    create_access_token,
)
from core.lib.exceptions import ConflictError
from core.lib.models import TimeStampModel

from .utils import dummyemailservice


class PermissionPolicy(TimeStampModel):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(server_default=false())
    permissions = Column(MutableList.as_mutable(ARRAY(String)), server_default="{}")
    staff_users: Mapped["StaffUser"] = relationship(back_populates="permission_policy")


class StaffUser(Base):
    id: Mapped[UUID] = mapped_column(default=uuid.uuid4, primary_key=True, index=True)
    role: Mapped[Literal["Backoffice", "Company"]]
    name: Mapped[str]
    username: Mapped[str] = mapped_column(unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    password: Mapped[str]
    password_history = Column(MutableList.as_mutable(ARRAY(String)), nullable=True)
    login_attempt: Mapped[int] = mapped_column(server_default="0")
    status: Mapped[Literal["Active", "Inactive", "Blocked", "Terminated", "Password Locked"]]
    status_remarks: Mapped[str | None]
    force_change_password: Mapped[bool] = mapped_column(server_default=true())
    password_updated_at: Mapped[datetime | None]
    password_reset_tokens: Mapped["PasswordResetToken"] = relationship(
        "PasswordResetToken",
        uselist=False,
        back_populates="staff_user",
        cascade="all, delete-orphan",
    )
    permission_policy_id: Mapped[int | None] = mapped_column(
        ForeignKey(PermissionPolicy.id)
    )
    permission_policy: Mapped[Optional[PermissionPolicy]] = relationship(
        back_populates="staff_users", lazy="joined"
    )
    is_superuser: Mapped[bool] = mapped_column(server_default=false())

    def create_token(self, expires_delta=None, token_type="access"):
        return create_access_token(
            data={
                "sub": self.name,
                "sid": str(self.id),
                "is_active": self.is_active,
                "mdi": self.phone_number,
                "udi": self.username,
                "emi": self.username,
                "scopes": [self.role, "Staff"],
            },
            expires_delta=expires_delta,
            token_type=token_type,
        )

    @classmethod
    def create(
        cls,
        db: Session,
        phone_number,
        username=None,
        name="Backoffice User",
        role="Backoffice",
        status="Active",
        status_remarks=None,
        password_updated_at=None,
        password_history=[],
        send_email=True,
    ):
        username = username or phone_number
        obj = cls(
            role=role,
            name=name,
            username=username,
            phone_number=phone_number,
            status=status,
            status_remarks=status_remarks,
            password_updated_at=password_updated_at,
            password_history=password_history,
        )
        password = generate_random_password()
        hashed_password = pwd_context.hash(password)
        obj.password = hashed_password
        obj.password_updated_at = datetime.now()
        obj.password_history = [hashed_password]
        obj.plain_password = password  # for sending plain password in email

        if (
            db.query(StaffUser)
            .filter(
                or_(
                    StaffUser.phone_number == phone_number,
                    StaffUser.username == username,
                )
            )
            .first()
        ):
            raise ConflictError(
                msg="Staff user is already registered with the provided phone number or username.",
                exception_type="staff_user.user_already_registered",
            )
        
        db.add(obj)
        db.commit()
        db.refresh(obj)

        if send_email:
            dummyemailservice.send(
                "send-email",
                {
                    "email": username,
                    "subject": "MMP-BO-password",
                    "body": f"Your password for back office login is {password}",
                },
            )

        return obj
    
    @property
    def is_active(self):
        return self.status == "Active"


class PasswordResetToken(Base):
    id: Mapped[UUID] = mapped_column(default=uuid.uuid4, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey(StaffUser.id, ondelete="CASCADE"))
    token: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    staff_user: Mapped["StaffUser"] = relationship(
        back_populates="password_reset_tokens",
    )
