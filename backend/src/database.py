from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from src.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Use NullPool for Supabase's connection pooler (PgBouncer in Transaction mode)
# Also increase connect timeout for remote database
engine = create_async_engine(
    settings.get_database_url,
    echo=False,  # Disable SQL logging to reduce noise
    future=True,
    poolclass=NullPool,  # Required for Supabase's PgBouncer
    connect_args={
        "timeout": 60,  # Connection timeout in seconds
        "command_timeout": 60,  # Query timeout
        "server_settings": {
            "statement_timeout": "60000",  # 60 seconds in milliseconds
        },
    },
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables - skipped when using Supabase with pre-created schema."""
    # Since we ran supabase_schema.sql directly in Supabase,
    # we don't need to create tables here
    pass
