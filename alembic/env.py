import os
from logging.config import fileConfig

from settings.database import Base
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from models import etter
from models import auth

POSTGRES_HOST = os.environ.get('ETTER_DB_HOST', 'localhost')
POSTGRES_PORT = os.environ.get('ETTER_DB_PORT', '5432')
POSTGRES_USER = os.environ.get('ETTER_DB_USER', 'user')
POSTGRES_PASSWORD = os.environ.get('ETTER_DB_PASSWORD', 'password')
POSTGRES_DB = os.environ.get('ETTER_DB_NAME', 'database')

DATABASE_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
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
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == "etter"
    elif type_ == "table":
        return parent_names.get("schema_name") == "etter"
    return True

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return object.schema == "etter"
    return True

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            include_schemas=True,
            include_object=include_object,
            version_table_schema='etter'
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()