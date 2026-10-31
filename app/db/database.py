import os
import sqlite3
from pathlib import Path
from typing import Generator, Optional
from contextlib import contextmanager
from app.db.schema import SCHEMA_SQL

# Data directory path: backend/data
BASE_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "codecompass.db"


def ensure_data_dir() -> Path:
    """Ensure backend data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


@contextmanager
def get_db(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a SQLite connection with foreign keys enabled."""
    target_path = db_path if db_path is not None else DB_PATH
    ensure_data_dir()
    con = sqlite3.connect(str(target_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    try:
        yield con
    finally:
        con.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database tables and FTS5 virtual tables."""
    target_path = db_path if db_path is not None else DB_PATH
    ensure_data_dir()
    with get_db(target_path) as con:
        con.executescript(SCHEMA_SQL)
        con.commit()
