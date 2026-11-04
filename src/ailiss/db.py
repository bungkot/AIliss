import logging
from collections.abc import Generator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine

from ailiss.config import database_path, get_settings

logger = logging.getLogger(__name__)


def create_database_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    local_path = database_path(url)
    if local_path is not None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    if url.startswith("sqlite"):
        return create_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    if url.startswith(("postgresql://", "postgresql+")):
        return create_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
            connect_args={"connect_timeout": int(settings.database_connect_timeout_seconds)},
        )
    raise ValueError("Unsupported database URL dialect")


engine = create_database_engine()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def database_is_ready() -> bool:
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1")).one()
        return True
    except SQLAlchemyError as exc:
        logger.warning("Database readiness check failed: %s", type(exc).__name__)
        return False
