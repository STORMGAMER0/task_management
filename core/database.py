from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from core.config import settings


engine = create_async_engine(settings.database_url, pool_size= settings.db_pool_size, max_overflow=settings.db_max_overflow,echo=settings.debug,future=True)

async_session_maker = async_sessionmaker(engine,class_=AsyncSession,expire_on_commit=False,autocommit = False, autoflush=False)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

