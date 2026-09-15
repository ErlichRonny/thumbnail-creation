from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

connect_args = {"ssl": "require"} if settings.database_ssl else {}

engine = create_async_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
