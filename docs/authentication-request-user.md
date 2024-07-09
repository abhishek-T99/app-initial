## Authentication using AuthenticationMiddleware

After using `AuthenticationMiddleware`, every request will have an `request.user` attribute, even if the user is not authenticated. If the user is not authenticated, `request.user.is_authenticated` flag will be `False`, and `request.user` will be an instance of `UnauthenticatedUser`. Otherwise, `request.user.is_authenticated` will be False and `request.user` will be an instance of `AuthUser` which has been implemented by subclassing `SimpleUser` model from `starlette`. <br><br>
To access this in ViewSet, we can do:

```python
from starlette.authentication import requires
from core.lib.viewsets import GenericViewSet
from core.lib.decorators import action


class UserViewSet(GenericViewSet):
    @action(detail=False, methods=["GET"])
    @requires(["authenticated"])
    async def me(self, request):
        if request.user.is_authenticated:
            return {
                "id": request.user.id,
                "phone_number": request.user.phone_number,
            }
        else:
            return {"detail": "Not authenticated"}
```

Here, we have used `requires` decorator to check the scope of a user (in this case it is `authenticated`) which returns whether user is authenticated or not. If the user is authenticated, we return the user's id and phone number. Otherwise, we return a message saying that the user is not authenticated. We are checking the scope `authenticated` because we have set the scope of `AuthUser` to `authenticated` in `core/lib/authentication.py`, in the case of successful authentication. In similar manner, we can set other scopes as per the role of the user, and check accordingly, for e.g., we can do so for admin users as well.
