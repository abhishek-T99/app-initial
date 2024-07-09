import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from psycopg2 import OperationalError
from psycopg2.errors import DatabaseError as Psycopg2DatabaseError
from sqlalchemy.exc import DatabaseError, IntegrityError

from core.config import config
from core.db.session import get_db_context
from core.lib.authentication import AuthenticationMiddleware, JWTAuthBackend

# from pathlib import Path

# BASE_DIR = Path(__file__).parent.parent

logger = logging.getLogger("uvicorn")


# To order tags in the OpenAPI schema
mobile_tags = []
manage_tags = []

mobile_tags_metadata = [{"name": x} for x in mobile_tags]
manage_tags_metadata = [{"name": x} for x in manage_tags]


def handle_db_error(request: Request, exc):
    with get_db_context() as db:
        db.rollback()
    raise exc


def create_app(**kwargs):
    swagger_ui_parameters = {
        "defaultModelsExpandDepth": -1,  # Disable Schemas shown in Swagger
        "displayRequestDuration": True,
        "persistAuthorization": True,
    }

    app = FastAPI(
        debug=config.debug, swagger_ui_parameters=swagger_ui_parameters, **kwargs
    )
    try:
        from core.debug.debug_toolbar import DebugToolbarMiddleware

        app.add_middleware(
            DebugToolbarMiddleware,
            panels=["core.debug.debug_toolbar.SQLAlchemyPanel"],
        )
    except ImportError:
        pass
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    if config.backoffice_url:
        origins.append(config.backoffice_url.rstrip("/"))

    app.add_middleware(
        AuthenticationMiddleware,
        backend=JWTAuthBackend(),
    )

    app.add_exception_handler(Psycopg2DatabaseError, handle_db_error)
    app.add_exception_handler(DatabaseError, handle_db_error)
    # The following two may not be required since the super classes are already handled.
    app.add_exception_handler(IntegrityError, handle_db_error)
    app.add_exception_handler(OperationalError, handle_db_error)

    # custom merchant exception

    # This has to be the last middleware to be added to the application.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def app_openapi(app, service_name, manage=False, tags={}):
    if not tags:
        tags = manage_tags_metadata if manage else mobile_tags_metadata
    if app.openapi_schema:
        return app.openapi_schema
    url = f"/{service_name}"
    if manage:
        url += "/manage"
    openapi_schema = get_openapi(
        title="Initial App API",
        version="0.2.0",
        description="Web Services for v2.0",
        routes=app.routes,
        tags=tags if tags else None,
        servers=[{"url": url}] if url else None,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/icon-white.svg"
    }
    return openapi_schema
