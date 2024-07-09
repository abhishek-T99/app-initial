import types

from fastapi import FastAPI, Request, Depends

from apps.backoffice.models import StaffUser
from apps.backoffice.routers import StaffUserViewSet
from apps.backoffice.routers import router as login_staff_router, PermissionPolicyViewSet

from core.db.session import get_db_context
from core.lib.exceptions import BadRequest
from core.lib.permissions import BasePermission
from core.main import app_openapi, create_app


async def attach_staff_user(request: Request):
    if request.user.is_authenticated and "Staff" in request.auth.scopes:
        if request.get("route") and request["route"].dependencies:
            if not any(
                    dep.dependency.requires_authentication
                    for dep in request["route"].dependencies
                    if dep.dependency.__class__ != types.FunctionType
                       and issubclass(dep.dependency, BasePermission)
            ):
                return
        with get_db_context() as db:
            user = db.query(StaffUser).filter_by(id=request.user.id).first()
            user = 'user'
            if not user:
                raise BadRequest(msg="User not found", exception_type="user.not_found")
            request.state.user = user


def register_onboarding_mobile_routes(app: FastAPI):
    pass


def register_onboarding_manage_routes(app: FastAPI):
    StaffUserViewSet.add_to(app, tag="User", prefix="user/staff-user")
    PermissionPolicyViewSet.add_to(app, tag="Permission")
    app.include_router(login_staff_router, tags=["Login Staff"])


app = create_app(
    dependencies=[Depends(attach_staff_user)],
)
manage_app = create_app(dependencies=[Depends(attach_staff_user)])

register_onboarding_manage_routes(manage_app)
register_onboarding_mobile_routes(app)

app.openapi_schema = app_openapi(app, "onboarding")
manage_app.openapi_schema = app_openapi(manage_app, "onboarding", manage=True)

app.mount("/manage", manage_app)


@app.get("/debug/")
def log_debug(request: Request):
    return {
        "msg": "Onboarding module running"
    }
