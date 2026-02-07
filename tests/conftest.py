import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shelflife.database import Base, get_session
from shelflife.app import create_app
import shelflife.models  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite://"  # in-memory

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session():
    async with TestSession() as s:
        yield s


@pytest.fixture
async def client():
    app = create_app()

    async def override_session():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
