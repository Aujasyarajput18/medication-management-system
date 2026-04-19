"""
Aujasya — Alembic Migration Environment
Configured for async PostgreSQL with asyncpg.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

# Import ALL models so Alembic sees their metadata
from app.models.base import Base
from app.models.user import User, OtpSession, RefreshToken, UserMealTime  # noqa: F401
from app.models.medicine import Medicine  # noqa: F401
from app.models.schedule import Schedule  # noqa: F401
from app.models.dose_log import DoseLog  # noqa: F401
from app.models.caregiver_link import CaregiverLink  # noqa: F401
from app.models.push_subscription import PushSubscription  # noqa: F401
from app.models.consent_record import ConsentRecord  # noqa: F401
from app.models.notification_log import NotificationLog  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with a given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' async mode."""
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
