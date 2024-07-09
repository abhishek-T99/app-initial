from abc import ABC, abstractmethod
from fastapi import HTTPException, Depends, Request
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

SAFE_METHODS = ["GET", "HEAD", "OPTIONS"]
api_key_header = APIKeyHeader(
    name="access-token", description="Authorization token", auto_error=False
)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/onboarding/manage/user/token", auto_error=False
)


# HTTP_METHOD_MAPPING = {
#     "GET": "Retrieve",
#     "POST": "Create",
#     "PATCH": "Update",
#     "DELETE": "Delete",
# }


class BasePermission(ABC):
    """
    Abstract permission that all other Permissions must be inherited from.

    Defines basic error message & status code.

    Upon initialization, calls abstract method `has_permission`
    which will be specific to concrete implementation of Permission class.

    You would write your permissions like this:

    ```python
    class TeapotUserAgentPermission(BasePermission):
        def has_permission(self, request: Request) -> bool:
            return request.headers.get('User-Agent') == "Teapot v1.0"
    ```
    """

    # TODO Make error message consistent, use from single place
    authentication_error_message = "You must be authenticated to perform this action."
    authentication_status_code = 401
    authorization_error_message = "You are not permitted to perform this action."
    authorization_status_code = 403

    requires_authentication = False

    @abstractmethod
    def has_permission(self, request: Request) -> bool: ...

    def __init__(self, request: Request):
        self.request = request
        if self.requires_authentication and not request.user.is_authenticated:
            if hasattr(request.state, "error"):
                raise request.state.error
            else:
                raise HTTPException(
                    status_code=self.authentication_status_code,
                    detail=self.authentication_error_message,
                )
        if not self.has_permission(request):
            raise HTTPException(
                status_code=self.authorization_status_code,
                detail=self.authorization_error_message,
            )


class IsAuthenticated(BasePermission):
    requires_authentication = True

    def __init__(self, request: Request, _: str = Depends(api_key_header)):
        super().__init__(request)

    def has_permission(self, request: Request) -> bool:
        return True


class IsStaffUser(IsAuthenticated):
    def __init__(self, request: Request, _: str = Depends(oauth2_scheme)):
        BasePermission.__init__(self, request)

    def has_permission(self, request: Request) -> bool:
        return (
            request.user.is_authenticated
            and request.user.is_active
            and "Staff" in request.auth.scopes
        )


class IsETUser(IsStaffUser):
    def has_permission(self, request: Request) -> bool:
        return super().has_permission(request) and "ET" in request.auth.scopes


class IsBranchUser(IsStaffUser):
    def has_permission(self, request: Request) -> bool:
        return super().has_permission(request) and "Branch" in request.auth.scopes


def get_view(endpoint):
    view = endpoint.view if hasattr(endpoint, "view") else endpoint.__self__
    return view


def get_permission_key(endpoint, method):
    view = get_view(endpoint)
    action = endpoint
    if view.model:
        model_name = view.model.__name__
    else:
        model_name = (
            view.__class__.__name__.replace("ViewSet", "")
            .replace("ViewSet", "")
            .replace("viewset", "")
        )
    if hasattr(action, "is_action"):
        if hasattr(action.__func__, "permission_key"):
            return model_name, action.__func__.permission_key
        action_name = action.__name__
        if method == "GET":
            action_name = f"View {action_name}"
    else:
        action_name = action.__name__.replace("_wrapper", "").replace(
            "initial_form_data", "update"
        )
    return model_name, action_name.replace("_", " ").strip().title()


class IsBackofficeUser(IsStaffUser):
    def has_permission(self, request: Request) -> bool:
        # permission_key = list(
        #     get_permission_key(request.get("endpoint"), request.method)
        # )
        return (
            super().has_permission(request) and "Backoffice" in request.auth.scopes
            # and check_permissions(request, permission_key) # gRPC to be studied later
        )


class IsUser(IsAuthenticated):
    def has_permission(self, request: Request) -> bool:
        return request.user.is_authenticated and "Staff" not in request.auth.scopes


class AllowAny(BasePermission):
    def has_permission(self, request: Request) -> bool:
        return True


class IsAuthenticatedOrReadOnly(IsAuthenticated):
    def has_permission(self, request: Request) -> bool:
        return request.method in SAFE_METHODS or request.user.is_authenticated


class IsUserOrReadOnly(IsAuthenticated):
    def has_permission(self, request: Request) -> bool:
        return request.method in SAFE_METHODS or (
            request.user.is_authenticated and "Staff" not in request.auth.scopes
        )


class ReadOnly(BasePermission):
    def has_permission(self, request: Request) -> bool:
        return request.method in SAFE_METHODS


class IsActiveMobileUser(IsAuthenticated):
    def has_permission(self, request: Request) -> bool:
        return (
            request.user.is_authenticated
            and request.user.is_active
            and "Staff" not in request.auth.scopes
        )


class IsETBOUser(IsAuthenticated):
    def has_permission(self, request: Request) -> bool:
        return (
            request.user.is_authenticated
            and request.user.is_active
            and ("Backoffice" in request.auth.scopes or "ET" in request.auth.scopes)
        )
