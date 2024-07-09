import os
import sys

sys.path.append(os.getcwd())

from core.alembic.base import config, run_migrations
from core.config import config as app_config


if app_config.environment != "dev":
    db_env_name = "DATABASE_URL"
else:
    db_env_name = "ONBOARDING_DATABASE_URL"

database_url = os.environ.get(db_env_name)
if not database_url:
    raise Exception(
        f"We couldn't find `{db_env_name}` in the environment. "
        f"Please verify `alembic` was run with `{db_env_name}` "
        "set to a valid database connection string "
        f"(e.g. `{db_env_name}=postgresql://user:pass@localhost:5432/onboarding`)"
    )
config.set_main_option("sqlalchemy.url", database_url)

run_migrations("onboarding")
