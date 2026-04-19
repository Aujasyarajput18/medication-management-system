"""
Aujasya — Test Configuration & Fixtures
Uses the Docker Compose PostgreSQL instance (aujasya_test database).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.base import Base
from app.models.user import User, UserMealTime

# Override database URL for testing
TEST_DATABASE_URL = settings.DATABASE_URL.replace("aujasya_dev", "aujasya_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test database session (rolls back after each test)."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_redis() -> AsyncGenerator[Redis, None]:
    """Provide a test Redis client (uses DB index 15 to avoid conflicts)."""
    redis = Redis.from_url(
        settings.REDIS_URL.rsplit("/", 1)[0] + "/15",
        decode_responses=True,
    )
    await redis.flushdb()
    yield redis
    await redis.flushdb()
    await redis.close()


@pytest_asyncio.fixture
async def client(db_session, test_redis) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated test HTTP client."""
    async def _override_db():
        yield db_session

    async def _override_redis(request):
        return test_redis

    app.dependency_overrides[get_async_session] = _override_db
    app.state.redis = test_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_patient(db_session) -> User:
    """Create a test patient user."""
    user = User(
        id=uuid.uuid4(),
        phone_number="+919876543210",
        phone_verified=True,
        role="patient",
        preferred_language="hi",
    )
    db_session.add(user)
    await db_session.flush()

    # Add default meal times
    default_meals = [
        ("waking", "06:00"),
        ("breakfast", "08:00"),
        ("lunch", "13:00"),
        ("dinner", "20:00"),
        ("bedtime", "22:00"),
    ]
    for meal_name, time_str in default_meals:
        from app.utils.timezone import parse_time

        meal_time = UserMealTime(
            user_id=user.id,
            meal_name=meal_name,
            typical_time=parse_time(time_str),
        )
        db_session.add(meal_time)

    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_caregiver(db_session) -> User:
    """Create a test caregiver user."""
    user = User(
        id=uuid.uuid4(),
        phone_number="+919876543211",
        phone_verified=True,
        role="caregiver",
        preferred_language="en",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_patient, test_redis) -> dict[str, str]:
    """Generate valid auth headers for the test patient."""
    import jwt as pyjwt

    now = datetime.utcnow()
    jti = str(uuid.uuid4())
    token = pyjwt.encode(
        {
            "sub": str(test_patient.id),
            "role": test_patient.role,
            "phone_last4": test_patient.phone_number[-4:],
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "jti": jti,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def caregiver_headers(test_caregiver, test_redis) -> dict[str, str]:
    """Generate valid auth headers for the test caregiver."""
    import jwt as pyjwt

    now = datetime.utcnow()
    token = pyjwt.encode(
        {
            "sub": str(test_caregiver.id),
            "role": "caregiver",
            "phone_last4": test_caregiver.phone_number[-4:],
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "jti": str(uuid.uuid4()),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
