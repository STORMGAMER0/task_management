from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from sqlalchemy import text
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

engine = create_async_engine(settings.database_url, pool_size= settings.db_pool_size, max_overflow=settings.db_max_overflow,echo=settings.debug,future=True)

async_session_maker = async_sessionmaker(engine,class_=AsyncSession,expire_on_commit=False,autocommit = False, autoflush=False)

Base = declarative_base()


async def init_db():

    logger.info("Verifying database connection...")
    from models.user import User
    from models.task import Task  # ← Make sure this exists
    from models.comment import Comment
    from models.tag import Tag, task_tags
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.critical(f"❌ Database connection failed: {e}")
        raise


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


async def close_db():

    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("✅ Database connections closed")

