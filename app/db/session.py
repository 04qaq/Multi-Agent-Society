from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import config

DATABASE_URL = (
    f"postgresql+asyncpg://{config.database.user}:{config.database.password}"
    f"@{config.database.host}:{config.database.port}/{config.database.name}"
)

engine = create_async_engine(DATABASE_URL, echo=config.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
