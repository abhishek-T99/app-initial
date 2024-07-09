import os

from core.alembic.base import config, run_migrations

config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL"))


run_migrations()