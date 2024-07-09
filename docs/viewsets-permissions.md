# ViewSet Permissions

Multiple supports have been added in ViewSet to support permissions in FastAPI. These are the changes:

*   `permission_classes` and `authentication` have been added in ViewSet

```python
class TestViewSet(GenericModelViewSet):
	...
	permissions_classes = [IsAuthenticated]
```

When we pass `permission_classes`, `authentication` will be considered as `True` which in turn, enables security padlock in Swagger UI, so that, we can enter `access-token` for all authentication-required APIs, rather than adding `access-token` in `Header` for each APIs individually.

Here, we can provide several classes available in `core/lib/permissions.py` to `permission_classes` such as `IsAuthenticated`, `IsUser`, `IsStaffUser`, `IsAuthenticatedOrReadOnly` and so on. It will check permissions for all the permission classes provided (AND operation). `IsAuthenticated` will just check whether user is authenticated or not. Similarly, `IsUser` will check whether user has `mobile_user` under auth scopes or not. For `IsStaffUser`, whether the user has `admin` auth scope or not will be checked. `IsAuthenticatedOrReadOnly` allows unauthenticated user to access `GET`, `HEAD` and `OPTIONS` request methods (which have been added to `SAFE_METHODS`). Also, there are several active user permission checks added, such as `IsActiveMobileUser`, `IsActiveAdminUser` and so on. <br>

*   There's one support added for `action` decorator. We can pass `permission_classes` as parameter. This will be like overriding ViewSet level permissions.

```python
@action(detail=False, permission_classes=[AllowAny])
def test_user(self):
	pass
```

By providing `AllowAny` inside `permission_classes`, this `test_user` will be exempted from permission checks. Or, we can provide other permissions as per the requirements. This feature allows user to override root level viewset permissions.
