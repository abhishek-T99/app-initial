from fastapi import Request
import types

from core.lib.permissions import BasePermission
from core.db.session import get_db_context
from apps.user.models import User
from core.lib.exceptions import BadRequest


async def attach_user(request: Request):
    if request.user.is_authenticated and "Staff" not in request.auth.scopes:
        if request.get("route") and request["route"].dependencies:
            if not any(
                    dep.dependency.requires_authentication
                    for dep in request["route"].dependencies
                    if dep.dependency.__class__ != types.FunctionType
                    and issubclass(dep.dependency, BasePermission)
            ):
                return
        with get_db_context() as db:
            user = db.query(User).filter_by(id=request.user.id).first()
            if not user:
                raise BadRequest(msg="User not found", exception_type="user.not_found")
            for x in user.__dir__():
                if x.startswith("__"):
                    continue
                setattr(request.user, x, getattr(user, x))
            request.state.user = user