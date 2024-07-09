import logging
import typing as t
from time import perf_counter

from debug_toolbar.panels.sql import SQLPanel
from debug_toolbar.middleware import (
    DebugToolbarMiddleware as DebugToolbarMiddlewareBase,
)
from debug_toolbar.settings import DebugToolbarSettings
from debug_toolbar.utils import import_string
from starlette.types import ASGIApp
from starlette.routing import NoMatchFound
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import APIRouter, Request, Response
from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.default import DefaultExecutionContext

from core.db.session import get_db

session = get_db().__next__()
log = logging.getLogger("uvicorn")


class DebugToolbarMiddleware(DebugToolbarMiddlewareBase):
    def __init__(self, app: ASGIApp, **settings: t.Any) -> None:
        BaseHTTPMiddleware.__init__(self, app)
        self.settings = DebugToolbarSettings(**settings)
        self.show_toolbar = import_string(self.settings.SHOW_TOOLBAR_CALLBACK)
        self.router: APIRouter = app  # type: ignore[assignment]

        while not isinstance(self.router, APIRouter):
            self.router = self.router.app
        try:
            self.router.url_path_for("debug_toolbar.render_panel")
        except NoMatchFound:
            self.init_toolbar()


# https://github.com/mongkok/fastapi-debug-toolbar/blob/main/debug_toolbar/panels/sqlalchemy.py
class SQLAlchemyPanel(SQLPanel):
    title = "SQLAlchemy"

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.engines: t.Set[Engine] = set()

    def register(self, engine: Engine) -> None:
        event.listen(engine, "before_cursor_execute", self.before_execute)
        event.listen(engine, "after_cursor_execute", self.after_execute)

    def unregister(self, engine: Engine) -> None:
        event.remove(engine, "before_cursor_execute", self.before_execute)
        event.remove(engine, "after_cursor_execute", self.after_execute)

    def before_execute(
        self,
        conn: Connection,
        cursor: t.Any,
        statement: str,
        parameters: t.Union[t.Sequence, t.Dict],
        context: DefaultExecutionContext,
        executemany: bool,
    ) -> None:
        conn.info.setdefault("start_time", []).append(perf_counter())

    def after_execute(
        self,
        conn: Connection,
        cursor: t.Any,
        statement: str,
        parameters: t.Union[t.Sequence, t.Dict],
        context: DefaultExecutionContext,
        executemany: bool,
    ) -> None:
        query = {
            "duration": (perf_counter() - conn.info["start_time"].pop(-1)) * 1000,
            "sql": statement,
            "params": parameters,
            "is_select": context.invoked_statement.is_select,
        }
        self.add_query(str(conn.engine.url), query)

    async def add_engines(self, request: Request):
        log.info("Loading database profiler...")
        self.engines.add(session.get_bind())

    async def process_request(self, request: Request) -> Response:
        await self.add_engines(request)

        for engine in self.engines:
            self.register(engine)
        try:
            response = await super().process_request(request)
        finally:
            for engine in self.engines:
                self.unregister(engine)
        return response
