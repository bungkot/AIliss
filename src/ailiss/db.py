from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from ailiss.config import database_path, get_settings


def create_database_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    local_path = database_path(url)
    if local_path is not None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=False, connect_args=connect_args)


engine = create_database_engine()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
