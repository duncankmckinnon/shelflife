from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from shelflife.config import DATABASE_URL


# NullPool is required for Vercel serverless — no connection reuse between Lambda invocations
engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
