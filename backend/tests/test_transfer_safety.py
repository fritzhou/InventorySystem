from pathlib import Path

import pytest

from app.scripts.migrate_database import _sqlite_path, transfer


def test_transfer_refuses_missing_sqlite_file(tmp_path: Path):
    missing = tmp_path / "typo.db"
    with pytest.raises(RuntimeError, match="existing SQLite"):
        transfer(f"sqlite:///{missing}", "postgresql+psycopg://user:pass@localhost/test", dry_run=True)
    assert not missing.exists()


def test_transfer_refuses_non_postgres_target(tmp_path: Path):
    source = tmp_path / "source.db"
    source.touch()
    with pytest.raises(RuntimeError, match="target must be PostgreSQL"):
        transfer(f"sqlite:///{source}", "sqlite:///:memory:", dry_run=True)


def test_relative_and_absolute_sqlite_paths_are_resolved_without_creation(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relative = Path("stockflow.db")
    relative.touch()
    absolute = tmp_path / "absolute.db"
    absolute.touch()
    assert _sqlite_path("sqlite:///./stockflow.db") == Path("./stockflow.db")
    assert _sqlite_path(f"sqlite:///{absolute}") == absolute
    for url, path in (("sqlite:///./missing.db", tmp_path / "missing.db"),
                      (f"sqlite:///{tmp_path / 'missing-absolute.db'}", tmp_path / "missing-absolute.db")):
        with pytest.raises(RuntimeError, match="existing SQLite"):
            transfer(url, "postgresql+psycopg://user:pass@localhost/test", dry_run=True)
        assert not path.exists()
