from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

engine = create_async_engine(
    str(settings.ASYNC_SQLALCHEMY_DATABASE_URI),
    echo=settings.ENVIRONMENT != "production",
    poolclass=NullPool
    if settings.ENVIRONMENT != "production"
    else AsyncAdaptedQueuePool,
    future=True,
)

SessionLocal = sessionmaker(  # type: ignore
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
)
