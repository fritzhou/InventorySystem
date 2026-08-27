from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
is_sqlite = settings.database_url.startswith("sqlite")
engine_options = {"pool_pre_ping": True}
if is_sqlite:
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update(pool_size=settings.db_pool_size, max_overflow=settings.db_max_overflow,
                          pool_timeout=settings.db_pool_timeout)
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Give each request its own database session and always close it."""
    with SessionLocal() as session:
        yield session
