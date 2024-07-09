from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Body, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from apps.backoffice.models import PasswordResetToken, PermissionPolicy, StaffUser
from apps.backoffice.permissions import PERMISSIONS
from apps.backoffice.schemas import (
    ForgotPasswordSchema,
    LoginResponse,
    PasswordChangeSchema,
    PermissionPolicyFormSchema,
    PermissionPolicyListSchema,
    PermissionPolicyRetrieveSchema,
    PermissionPolicyUpdateSchema,
    ResetPasswordSchema,
    StaffUserFormSchema,
    StaffUserReadSchema,
    ValidateResetTokenSchema,
)
from apps.backoffice.utils import get_formatted_permissions
from core.db.session import get_db
from core.lib.authentication import REFRESH_TOKEN_EXCEPTION, decode_token, get_password_hash, verify_password
from core.lib.decorators import action
from core.lib.exceptions import BadRequest
from core.lib.permissions import AllowAny, IsBackofficeUser
from core.lib.viewsets import ListViewSetProtocol, ModelViewSet, ViewSetProtocol
from sqlalchemy.orm import Session
from .helpers import authenticate_staff_user, generate_password_reset_token
from .utils import dummyemailservice


router = APIRouter(prefix="/user")


@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    db: Session = Depends(get_db),
):
    user = authenticate_staff_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != "Active":
        raise BadRequest(
            exception_type=f"user.{str(user.status).lower()}",
            msg=f"Sorry, your user status is {user.status}. "
                "Please contact the system administrator to reactivate your account.",
        )
    if user.password_updated_at:
        if user.password_updated_at < datetime.now() - timedelta(days=90):
            user.force_change_password = True
            db.commit()

    response = {
        "access_token": user.create_token(),
        "refresh_token": user.create_token(
            token_type="refresh",
            expires_delta=datetime.now().replace(hour=23, minute=59, second=59) - datetime.now(),
        ),
        "token_type": "bearer",
        "password_expiry_date": user.password_updated_at + timedelta(days=90) if user.password_updated_at else None,
        "user": {
            "name": user.name,
            "id": user.id,
            "force_change_password": user.force_change_password,
        },
    }
    if user.role == "Backoffice":
        if user.is_superuser:
            response["permissions"] = get_formatted_permissions(PERMISSIONS)
        elif user.permission_policy_id and user.permission_policy.is_active:
            response["permissions"] = get_formatted_permissions(
                user.permission_policy.permissions
            )
        elif user.permission_policy_id and not user.permission_policy.is_active:
            response["permissions"] = []
    return response


class PermissionPolicyViewSet(ModelViewSet):
    model = PermissionPolicy
    list_schema = PermissionPolicyListSchema
    read_schema = PermissionPolicyRetrieveSchema
    create_schema = PermissionPolicyFormSchema
    update_schema = PermissionPolicyUpdateSchema
    permission_classes = [IsBackofficeUser]
    prefix = "permissions"

    @action(method="GET", detail=False, permission_classes=[AllowAny])
    def default(self):
        permissions = get_formatted_permissions(PERMISSIONS)
        return {"msg": "list of all available permissions", "data": permissions}


def get_user(db, username: str):
    return db.query(StaffUser).filter(StaffUser.username == username).first()


class StaffUserViewSet(ModelViewSet):
    model = StaffUser
    schema = StaffUserReadSchema
    form_schema = StaffUserFormSchema
    permission_classes = [IsBackofficeUser]

    def _list_wrapper(
        self: ListViewSetProtocol,
        request: Request,
        search: str | None = None,
        db: Session = Depends(get_db),
    ):
        return super()._list_wrapper(request, db)

    def filter_list_queryset(self, queryset):
        if "search" in self.request.query_params:
            searched_item = self.request.query_params["search"]
            queryset = self.db.query(self.model).filter(
                (self.model.username.ilike(f"%{searched_item}%"))
                | (self.model.name.ilike(f"%{searched_item}%"))
                | (self.model.phone_number.ilike(f"%{searched_item}%"))
            )

        return queryset.order_by(self.model.name)

    def validate_staff_user(self, body: StaffUserFormSchema):
        if body.role != "Backoffice":
            raise BadRequest(
                msg="Company, Agent and Branch should be None for Backoffice",
                exception_type="staff_create_error.company_agent_branch_not_none",
            )

    def create(self, body):
        self.validate_staff_user(body)
        user = StaffUser.create(self.db, **body.dict())
        return user

    def update(self, id: int | UUID, body: BaseModel):
        self.validate_staff_user(body)
        obj = self.db.query(self.model).filter(self.model.id == id)
        staff_user = obj.first()
        data_to_update = body.dict()
        send_activation_email = False
        if body.status != staff_user.status:
            if staff_user.id == self.request.user.id:
                raise BadRequest(
                    msg="Staff User can't change own status.",
                    exception_type="staff_user.cannot_change_own_status",
                )
            if body.status == "Inactive":
                raise BadRequest(
                    msg="Staff User can't be inactive.",
                    exception_type="staff_user.cannot_inactive",
                )
            if not staff_user.status == "Active":
                if body.status in ["Blocked", "Terminated", "Password Locked"]:
                    raise BadRequest(
                        msg="Staff User can't be blocked or terminated if not active.",
                        exception_type="staff_user.cannot_block_terminate_inactive",
                    )
                elif body.status == "Active":
                    send_activation_email = True

        obj.update(data_to_update)
        self.db.commit()
        self.db.refresh(staff_user)
        if send_activation_email:
            # email_body = render_template(
            #     "reactivate_account.html",
            #     name=staff_user.name,
            #     username=staff_user.username,
            # )
            dummyemailservice.send(
                "send-email",
                {
                    "email": staff_user.username,
                    "subject": "Account Reactivation Confirmation",
                    "body": "email_body",
                },
            )
        return staff_user

    def delete(
        self: ViewSetProtocol,
        id: int | UUID,
        request: Request,
        db: Session = Depends(get_db),
    ):
        if request.user.id == id:
            raise BadRequest(
                msg="Staff User can't delete oneself.",
                exception_type="staff_user.cannot_delete_oneself",
            )
        return super().delete(id, request, db)

    @action(detail=False, method="POST")
    def reset_password(self, body: ResetPasswordSchema, request: Request):
        user = get_user(self.db, request.user.username)
        if not verify_password(body.old_password, user.password):
            raise BadRequest(
                msg="Password did not match",
                exception_type="login_error.invalid_password",
            )
        if user.password_history is None:
            user.password_history = [user.password]
        if any(
            verify_password(body.new_password, password)
            for password in user.password_history[-5:]
        ):
            raise BadRequest(
                msg="New password cannot be the same as any of the last 5 passwords",
                exception_type="login_error.invalid_password",
            )
        user.password = get_password_hash(body.new_password)
        user.force_change_password = False
        user.password_updated_at = datetime.now()
        user.password_history.append(user.password)
        if len(user.password_history) > 5:
            user.password_history.pop(0)
        self.db.commit()
        return {"msg": "Password has been reset successfully."}

    @action(detail=False, method="POST", permission_classes=[AllowAny])
    def forgot_password(self, body: ForgotPasswordSchema):
        user = get_user(self.db, body.username)
        if not user:
            raise BadRequest(msg="User not found", exception_type="user.not_found")
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id
        ).delete()
        token = generate_password_reset_token()
        reset_token = PasswordResetToken(token=token, user_id=user.id)
        reset_link = token={token}
        # contact_redirect_link = "https://www.dummyurl.com"
        # email_body = render_template(
        #     "forgot_password.html",
        #     username=user.name,
        #     reset_link=reset_link,
        #     contact_redirect_link=contact_redirect_link,
        # )
        dummyemailservice.send(
                "send-email",
                {
                "email": body.username,
                "subject": "MMP-BO-password",
                "reset_token": reset_link,
                "body": "email_body",
            },
            )
        self.db.add(reset_token)
        self.db.commit()
        return {"msg": "Password reset email has been sent."}

    @action(detail=False, method="POST", permission_classes=[AllowAny])
    def validate_reset_token(self, body: ValidateResetTokenSchema):
        reset_token = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token == body.token)
            .first()
        )
        if not reset_token:
            raise BadRequest(
                msg="Token is either invalid or expired",
                exception_type="login_error.invalid_token",
            )
        return {"msg": "Password Reset token is valid."}

    @action(detail=False, method="POST", permission_classes=[AllowAny])
    def set_password(self, body: PasswordChangeSchema, request):
        reset_token = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token == body.token)
            .first()
        )
        if not reset_token:
            raise BadRequest(
                msg="Token is either invalid or expired",
                exception_type="login_error.invalid_token",
            )
        user = reset_token.staff_user
        if user.password_history is None:
            user.password_history = [user.password]
        if any(
            verify_password(body.new_password, password)
            for password in user.password_history[-5:]
        ):
            raise BadRequest(
                msg="New password cannot be the same as any of the last 5 passwords",
                exception_type="login_error.invalid_password",
            )
        user.password = get_password_hash(body.new_password)
        user.force_change_password = False
        user.password_updated_at = datetime.now()
        user.password_history.append(user.password)
        if len(user.password_history) > 5:
            user.password_history.pop(0)
        self.db.delete(reset_token)
        self.db.commit()
        return {
            "msg": "Password has been set successfully.",
        }

    @action(detail=False, method="POST", permission_classes=[AllowAny])
    def refresh(self, refresh_token: Annotated[str, Body(embed=True)]):
        payload, _ = decode_token(refresh_token, token_type="refresh")
        if not payload:
            raise REFRESH_TOKEN_EXCEPTION
        user = self.db.query(StaffUser).filter_by(id=payload["sid"]).first()
        if not user:
            raise BadRequest(
                msg="User not found", exception_type="login_error.user_not_found"
            )
        if user.status != "Active":
            raise BadRequest(
                msg="User is not active", exception_type="login_error.user_inactive"
            )
        return {"access_token": user.create_token()}
