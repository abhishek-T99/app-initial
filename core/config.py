import logging
import os
from datetime import timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseSettings, AnyUrl

BASE_DIR = Path(__file__).parent.parent

log = logging.getLogger("uvicorn")


# class KafkaConfig(BaseSettings):
#     bootstrap_servers: str
#     sasl_mechanism: str = "SCRAM-SHA-512"
#     security_protocol: str = "SASL_SSL"
#     sasl_plain_username: str | None = None
#     sasl_plain_password: str | None = None
#     group_id: str


class InfluxConfig(BaseSettings):
    enable: bool = False
    url: str = "https://www.influx.com"
    token: str = "xxx"
    org: str = "xxx"


class RedisConfig(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None


class DatabaseConfig(BaseSettings):
    # TODO  place db connection string and connection pool setting here
    pass


class AuthTokenConfig(BaseSettings):
    bo_access_token_expiry_minutes: int = 15  # 15 minutes
    user_access_token_expiry_minutes: int = 1440  # 24 hours


# class EmailConfig(BaseSettings):
#     smtp_server: str | None = None
#     smtp_port: int | None = None
#     smtp_username: str | None = None
#     smtp_password: str | None = None
#     from_email: str | None = None

#     @property
#     def sender_email(self):
#         return self.from_email or self.smtp_username


class Config(BaseSettings):
    environment: str = "dev"
    service_name: str = "gateway"
    testing: bool = False
    debug: bool = False
    database_url: AnyUrl | str
    backoffice_url: AnyUrl | None = None
    base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

    # mock_email: bool = False
    # mock_firebase: bool = False
    # mock_otp: bool = True

    influx: InfluxConfig
    redis: RedisConfig = RedisConfig()
    auth_token: AuthTokenConfig = AuthTokenConfig()
    # kafka: KafkaConfig | None = None
    # enable_kafka: bool = True

    log_exceptions: bool = False
    log_exclude_exception_codes: list[str] = [
        "404",
    ]

    # storage config
    storage_class: Literal["S3Storage", "FileSystemStorage"] = "S3Storage"

    otp_expiration_seconds: int = 300
    google_application_credentials: str | None = None

    default_timezone = timezone(timedelta(hours=8))  # malaysian timezone (utc+8)
    # now = text(
    #     "timezone('Asia/Kuala_Lumpur', CURRENT_TIMESTAMP)"
    # )  # default datetime to use in models instead of func.now()
    # tz_locale = "Asia/Kuala_Lumpur"

    aes_key: str | None = None
    cloudfront_s3_proxy_url: str | None = None
    # TODO Nested complex types like `list` is not supported in v1
    # Issue: https://github.com/pydantic/pydantic-settings/issues/41
    # This has been fixed in v2
    # Nest this to run kafka once we upgrade to pydantic v2
    # kafka_topics: List[str] = []
    notification_sound: str = "default"

    class Config:  # type: ignore
        """
        Configuration class for managing environment variables.

        Attributes:
            env_file (str): The name of the environment file.
            env_nested_delimiter (str): The delimiter used for nested environment variables.
        """

        env_file = ".env"
        env_nested_delimiter = "__"


@lru_cache()
def get_config() -> Config:
    log.info("Loading config settings from the environment...")
    return Config()  # type: ignore # will read from .env file


config = get_config()
