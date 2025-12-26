from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

DEFAULT_APP_DIR = Path(os.getenv("MESSAGE_HUB_HOME", str(Path.home() / ".message_hub")))
DEFAULT_DB_PATH = DEFAULT_APP_DIR / "message_hub.sqlite"


@dataclass(frozen=True)
class DatabaseConfig:
    db_path: Path = DEFAULT_DB_PATH

    @property
    def url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"


def ensure_parent_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def make_engine(cfg: DatabaseConfig) -> Engine:
    ensure_parent_dir(cfg.db_path)
    return create_engine(cfg.url,
    query_cache_size=0,
     future=True)


def make_session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
