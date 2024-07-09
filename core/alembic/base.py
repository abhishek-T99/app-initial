import logging
from collections.abc import Iterable
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine.reflection import Inspector

from alembic import context
from alembic.environment import MigrationContext
from alembic.operations import MigrationScript
from core.db import load_models

load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
logger = logging.getLogger("alembic.env")


# add your model's MetaData objects here
# for 'autogenerate' support.  These must be set
# up to hold just those tables targeting a
# particular database. table.tometadata() may be
# helpful here in case a "copy" of
# a MetaData is needed.
# from myapp import mymodel
# target_metadata = {
#       'engine1':mymodel.metadata1,
#       'engine2':mymodel.metadata2
# }

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def load_metadata(service_name: str | None = None):
    load_models(service_name)
    from core.db import Base

    return Base.metadata


def table_exists(op, table_name):
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def run_migrations_offline(service_name: str | None = None, **kwargs) -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=load_metadata(service_name),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=True,
        compare_type=True,
        **kwargs,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online(service_name=None, **kwargs) -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    def process_revision_directives(
        context: MigrationContext,
        revision: str | Iterable[str | None] | Iterable[str],
        directives: list[MigrationScript],
    ):
        assert config.cmd_opts is not None
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            assert script.upgrade_ops is not None
            if script.upgrade_ops.is_empty():
                directives[:] = []

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=load_metadata(service_name),
            compare_server_default=True,
            compare_type=True,
            process_revision_directives=process_revision_directives,
            **kwargs,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations(service_name=None, **kwargs) -> None:
    if context.is_offline_mode():
        run_migrations_offline(service_name, **kwargs)
    else:
        run_migrations_online(service_name, **kwargs)
