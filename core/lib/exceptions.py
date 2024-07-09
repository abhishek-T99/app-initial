import json
from typing import Any, Dict

from fastapi import HTTPException
from core.influx import Point, ilog
from core.config import config


class BaseException(HTTPException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
        status_code: int = 400,
    ) -> None:
        self.msg = msg
        if detail is None:
            dct = {"type": exception_type}
            if msg:
                dct["msg"] = msg
            if loc:
                dct["loc"] = loc  # type: ignore
            detail = [dct]
        if (
            config.influx.enable
            and config.log_exceptions
            and str(status_code) not in config.log_exclude_exception_codes
        ):
            point = (
                Point("exception")
                .tag("code", str(status_code))
                .tag("environment", config.environment)
                .field("type", exception_type)
                .field("msg", msg)
                .field("detail", json.dumps(detail))
            )
            ilog(point)
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class InvalidData(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=422,
        )


class BadRequest(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=400,
        )


class NotFound(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=404,
        )


class SuspiciousError(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=510,
        )


# Success response is not an error, can be raised in any view to bypass validation of response_model and send a success message to the client
# use carefully


class SuccessResponse(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=200,
        )


class LimitExceeded(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=429,
        )


class AuthenticationError(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=401,
        )


class AuthorizationError(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=403,
        )


class ConflictError(BaseException):
    def __init__(
        self,
        exception_type: str,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=409,
        )


class InvalidForeignKey(BaseException):
    def __init__(
        self,
        exception_type: str | None = None,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        table: str | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        if not msg:
            msg = (
                f"Invalid foreign key value for {table}"
                if table
                else "Invalid foreign key value"
            )
        if not exception_type:
            exception_type = (
                f"integrity_error.invalid_foreign_key.{table}"
                if table
                else "integrity_error.invalid_foreign_key"
            )
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=422,
        )


class ForeignKeyProtectedException(BaseException):
    def __init__(
        self,
        exception_type: str | None = None,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        constraint: str | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        if not msg:
            msg = (
                f"Cannot delete when foreign key is still referenced. Constraint: {constraint}"
                if constraint
                else "Cannot delete when foreign key is still referenced"
            )
        if not exception_type:
            exception_type = (
                f"integrity_error.deletion_failure_foreign_key_reference.{constraint}"
                if constraint
                else "integrity_error.deletion_failure_foreign_key_reference"
            )
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=422,
        )


class TimeoutException(BaseException):
    def __init__(
        self,
        exception_type: str | None = None,
        msg: str | None = None,
        loc: list[str] | None = None,
        detail: Any | None = None,
        headers: Dict[str, Any] | None = None,
    ) -> None:
        if not exception_type:
            exception_type = "connection_timeout"
        if not msg:
            msg = "Connection Timeout."
        super().__init__(
            exception_type,
            msg=msg,
            loc=loc,
            detail=detail,
            headers=headers,
            status_code=408,
        )
