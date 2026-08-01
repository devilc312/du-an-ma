import os
from collections.abc import AsyncGenerator

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_NAME = "todo_test"
TEST_DATABASE_URL = f"postgresql+asyncpg://todo:todo@localhost:5432/{TEST_DATABASE_NAME}"
TEST_REDIS_URL = "redis://localhost:6379/15"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL
os.environ["ENVIRONMENT"] = "test"

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def database_schema() -> AsyncGenerator[None, None]:
    admin = await asyncpg.connect(
        user="todo",
        password="todo",
        database="postgres",
        host="localhost",
        port=5432,
    )
    try:
        exists = await admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            TEST_DATABASE_NAME,
        )
        if not exists:
            await admin.execute(f'CREATE DATABASE "{TEST_DATABASE_NAME}"')
    finally:
        await admin.close()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    redis = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await redis.flushdb()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client
    await redis.flushdb()
    await redis.aclose()
    app.dependency_overrides.clear()
