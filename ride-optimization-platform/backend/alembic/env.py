"""
Alembic Environment Configuration.

This module configures Alembic to:
- Use async SQLAlchemy engine
- Load database URL from app settings
- Discover all models for autogenerate
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import settings for database URL
from app.core.config import settings

# Import Base and all models for autogenerate support
# This ensures Alembic can detect model changes
from app.db.base import Base
from app.db.models import RideDB  # noqa: F401 - imported for side effects

# Alembic Config object - provides access to alembic.ini
config = context.config

# Override sqlalchemy.url with our settings
# This allows using environment variables instead of hardcoded URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))

# Setup Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData object for 'autogenerate' support
# Alembic compares this against the database to detect changes
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL scripts without connecting to the database.
    Useful for:
    - Reviewing what migrations will do
    - Applying migrations on systems without direct DB access
    - Version control of migration SQL
    
    In offline mode, we just emit SQL to stdout or a file.
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


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations with the given connection.
    
    This is called by both sync and async run modes.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Compare types to detect column type changes
        compare_type=True,
        # Compare server defaults
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode.
    
    Creates an async engine and runs migrations within a connection.
    This is the recommended approach for async SQLAlchemy applications.
    """
    # Create async engine from config
    # Note: We need to use psycopg2 for migrations (not asyncpg)
    # because Alembic doesn't fully support asyncpg
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Connects to actual database and applies migrations.
    Uses asyncio for async engine support.
    """
    asyncio.run(run_async_migrations())


# =============================================================================
# Entry Point
# =============================================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
