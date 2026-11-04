import os
import subprocess
import sys
from pathlib import Path

from ailiss.db import create_database_engine


def run_alembic(root: Path, database_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )


def test_postgresql_engine_uses_bounded_pool_settings():
    engine = create_database_engine(
        "postgresql+psycopg://ailiss:ailiss@127.0.0.1:5432/ailiss"
    )

    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10


def test_phase3_migration_rolls_back_and_upgrades(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    migration_file = (tmp_path / "migration.db").resolve().as_posix()
    database_url = f"sqlite:///{migration_file}"

    run_alembic(root, database_url, "upgrade", "head")
    current = run_alembic(root, database_url, "current")
    assert "003_phase3" in current.stdout

    run_alembic(root, database_url, "downgrade", "002_phase2")
    current = run_alembic(root, database_url, "current")
    assert "002_phase2" in current.stdout

    run_alembic(root, database_url, "upgrade", "head")
