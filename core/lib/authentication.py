import secrets
import string
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from jose import jwt
from passlib.context import CryptContext
from starlette.authentication import (
    AuthenticationBackend,
    SimpleUser,
    AuthCredentials,
)
from starlette.middleware.authentication import (
    AuthenticationMiddleware as BaseAuthMiddleware,
    AuthenticationError as StarletteAuthenticationError,
)
from starlette.requests import HTTPConnection
from starlette.responses import Response

from core.config import config
from core.lib.exceptions import AuthenticationError, BadRequest
from core.redis import cache

AUTHENTICATION_EXCEPTION = AuthenticationError(
    exception_type="user.not_authenticated",
    msg="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

REFRESH_TOKEN_EXCEPTION = BadRequest(
    exception_type="user.invalid_refresh_token",
    msg="Could not validate refresh token",
)

# to get a string like this run:
# openssl rand -hex 32
# TODO Security
# TODO Different SECRET_KEY for access_token for Staff Users
SECRET_KEY = "bc23abe266edfec1dd3a062b3c242b7b949471aa74beac952b5a882efd478918"
REFRESH_SECRET_KEY = "ccf53bf7778a1faeaaf3aeac0b22eb870c54c128c7e3ce9bd097736735fb4823"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(
        data: dict, expires_delta: timedelta | None = None, token_type="access"
):
    to_encode = data.copy()
    if not expires_delta:
        # if token_type == "access":
        #     expires_delta = timedelta(
        #         minutes=config.auth_token.bo_access_token_expiry_minutes
        #     )
        # else:
        #     expires_delta = timedelta(
        #         minutes=config.auth_token.bo_refresh_token_expiry_minutes
        #     )
        expires_delta = timedelta(
                minutes=config.auth_token.bo_access_token_expiry_minutes
            )

    secret = REFRESH_SECRET_KEY if token_type == "refresh" else SECRET_KEY
    expire = datetime.now() + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.now()})
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=ALGORITHM)
    return encoded_jwt


def get_token_type(iat, exp):
    if (
            datetime.fromtimestamp(exp) - datetime.fromtimestamp(iat)
    ).total_seconds() == config.auth_token.bo_access_token_expiry_minutes * 60:
        return "access"
    else:
        return "refresh"


def decode_token(token: str, token_type: Literal["access", "refresh"] = "access"):
    if not token:
        return None, []
    scopes = []
    try:
        secret = REFRESH_SECRET_KEY if token_type == "refresh" else SECRET_KEY
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        username: str | None = payload.get("udi")
        iat: int = payload.get("iat")
        exp: int = payload.get("exp")
        scopes = payload.get("scopes", [])
        if username is None:
            raise AUTHENTICATION_EXCEPTION
        if "Backoffice" in scopes and (iat and exp) and token_type != get_token_type(iat, exp):
            raise AUTHENTICATION_EXCEPTION
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(
            exception_type="user.token_expired",
            msg="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        if token_type == "refresh":
            raise REFRESH_TOKEN_EXCEPTION
        else:
            raise AUTHENTICATION_EXCEPTION
    if "Staff" in payload.get("scopes", []):
        scopes.extend(payload.get("scopes", []))
    return payload, scopes


def generate_random_password():
    while True:
        password_length = secrets.randbelow(3) + 8
        password = "".join(
            secrets.choice(string.ascii_letters + string.digits + "*&^%$#@!")
            for _ in range(password_length)
        )
        if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!#$%&'()*+,-./:;<=>?@[\]^_`{|}~" for c in password)
                and not any(c.isspace() for c in password)
        ):
            return password


class AuthenticationMiddleware(BaseAuthMiddleware):
    @staticmethod
    def default_on_error(conn: HTTPConnection, exc: StarletteAuthenticationError) -> Response:
        if len(exc.args) and hasattr(exc.args[0], "detail"):
            detail = exc.args[0].detail
        else:
            detail = str(exc) or "Could not validate credentials."
        return JSONResponse({"detail": detail}, status_code=401)


class AuthUser(SimpleUser):
    def __init__(self, payload):
        self.username = payload.get("udi")
        self.id = UUID(payload["sid"]) if payload.get("sid") else None
        self.phone_number = payload.get("udi")
        self.is_active = payload.get("is_active")
        self.name = payload.get("sub")
        self.jti = payload.get("jti")
        self.email = payload.get("emi")

    @property
    def display_name(self) -> str:
        return self.username or self.phone_number or ""


def validate_user_and_device(user_id, access_token_id, device_id):
    if device_id:
        device_blocked = cache.get(f"deviceblock:{device_id}")
        if device_blocked:
            raise HTTPException(
                status_code=420,
                detail="Device Blocked",
                headers={"X-expired-at": datetime.now(config.default_timezone).replace(tzinfo=None).isoformat()}
            )
    if user_id:
        user_blocked = cache.get(f"userblock:{user_id}")
        if user_blocked:
            raise HTTPException(
                status_code=420,
                detail="User Blocked",
                headers={"X-expired-at": datetime.now(config.default_timezone).replace(tzinfo=None).isoformat()}
            )
    if access_token_id:
        cache_token_id = cache.get(f"jti:{user_id}")
        if cache_token_id.decode("utf-8") == access_token_id:
            return
        elif cache_token_id.decode("utf-8") != access_token_id:
            raise HTTPException(
                status_code=420,
                detail="You have multiple sessions open at the same time. For security reasons, "
                       "this session will be terminated.",
                headers={"X-expired-at": datetime.now(config.default_timezone).replace(tzinfo=None).isoformat()}
            )


def validate_auth_header(request):
    authorization = request.headers["Authorization"].split()
    if len(authorization) != 2:
        raise AUTHENTICATION_EXCEPTION
    elif authorization[0].lower() != "bearer":
        raise AUTHENTICATION_EXCEPTION
    else:
        return authorization[1]


class JWTAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection):
        # TODO Verify and remove X-Validate-Biometric
        if (
                "access-token" not in conn.headers
                or ("access-token" in conn.headers and not conn.headers["access-token"])
                or (
                        "X-Validate-Biometric" in conn.headers
                        and conn.headers["X-Validate-Biometric"] == "true"
                )
        ) and "Authorization" not in conn.headers:
            return
        elif "Authorization" in conn.headers:
            try:
                auth = validate_auth_header(conn)
            except HTTPException as e:
                conn.state.error = e
                return
        else:
            auth = conn.headers["access-token"]

        try:
            payload, scopes = decode_token(auth)
            if payload:
                scopes.append("authenticated")
            if "Staff" not in scopes and config.service_name not in ["authx", "gateway"]:
                validate_user_and_device(payload.get("sid"), payload.get("jti"), conn.headers.get("device-id"))
            return AuthCredentials(scopes), AuthUser(payload)
        except HTTPException as e:
            conn.state.error = e
            return
