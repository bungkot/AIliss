from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

import ailiss.db as db
from ailiss.main import app


@pytest.fixture
def tmp_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    test_engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr(db, "engine", test_engine)
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def client(tmp_database: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    import ailiss.db as db_module

    def override_session():
        with Session(db_module.engine) as session:
            yield session

    app.dependency_overrides[db.get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
