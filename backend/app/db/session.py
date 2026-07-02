"""
Waypoint API — Database Session

SQLAlchemy async engine + sessionmaker + FastAPI dependency.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import AsyncGenerator

from app.config import settings

# Async engine — uses asyncpg driver
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Called on app startup — connection pool is lazily initialized by SQLAlchemy,
    but this is a hook for any future startup logic (e.g. checking connectivity)."""
    # Verify connectivity
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("SELECT 1")
        )


async def close_db() -> None:
    """Called on app shutdown — dispose of the engine's connection pool."""
    await engine.dispose()
