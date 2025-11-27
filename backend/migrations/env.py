from logging.config import fileConfig
import os
import sys
from pathlib import Path
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# In Docker, environment variables are passed directly, so .env may not exist
# Try multiple locations: project root (local dev), backend dir, current dir
for env_path in [
    Path(__file__).parent.parent.parent / ".env",  # project root (local dev)
    Path(__file__).parent.parent / ".env",          # backend dir
    Path(".env"),                                    # current dir
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# Override sqlalchemy.url from .env
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Fix legacy postgres:// scheme for SQLAlchemy 2.x
    # SQLAlchemy 2.x removed the "postgres" dialect alias; it requires "postgresql"
    # Many providers (Heroku, Render, Coolify) still use postgres:// in DATABASE_URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    config.set_main_option('sqlalchemy.url', database_url)

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
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
