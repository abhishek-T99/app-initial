from fastapi import FastAPI, Depends, Request

from apps.user.routers.manage import ManageUserViewSet
from core.main import app_openapi, create_app
from .dependencies import attach_user


def register_user_manage_routes(app: FastAPI):
    ManageUserViewSet.add_to(app, tag="User", prefix="user")


def register_user_mobile_routes(app: FastAPI):
    pass


# app = create_app(dependencies=[Depends(attach_user), Depends(validate_user_and_device)])
app = create_app(dependencies=[Depends(attach_user)])

manage_app = create_app()

register_user_manage_routes(manage_app)
register_user_mobile_routes(app)

app.openapi_schema = app_openapi(app, "authentication")
manage_app.openapi_schema = app_openapi(manage_app, "authentication", manage=True)

app.mount("/manage", manage_app)


@app.get("/debug/")
def log_debug(request: Request):
    return {
        "msg": "Authentication module running",
        "client_ip": request.client.host,
        "forwarded_ip": request.headers.get("X-Forwarded-For"),
    }
