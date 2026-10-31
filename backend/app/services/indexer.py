"""SQLite & FTS5 Indexing Service.

Atomically indexes parsed repository files and symbols into SQLite relational tables
and FTS5 virtual tables inside a transaction context.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.db.database import get_db, DB_PATH
from app.services.ast_parser import ParsedFileResult, FailedFileResult, parse_python_file


def index_repository_contents(
    repo_name: str,
    python_files: Dict[str, str],
    db_path: Optional[Path] = None,
) -> Tuple[str, int, int, int, List[FailedFileResult]]:
    """Index extracted Python source files into SQLite and FTS5 atomically.

    Args:
        repo_name: Repository name.
        python_files: Mapping of repo-relative path to source code.
        db_path: Database file path.

    Returns:
        Tuple containing:
            - repo_id: Unique UUID string for the repository
            - total_files: Number of successfully indexed files
            - total_symbols: Total count of extracted symbols
            - total_lines: Total lines of code across indexed files
            - failed_files: Files that had syntax/encoding errors and were skipped
    """
    repo_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()

    parsed_results: List[ParsedFileResult] = []
    failed_files: List[FailedFileResult] = []

    # 1. Parse all files in memory with AST visitor
    total_lines = 0
    for path, code in python_files.items():
        parsed, failed = parse_python_file(path, code)
        if parsed:
            parsed_results.append(parsed)
            total_lines += parsed.line_count
        elif failed:
            failed_files.append(failed)

    if not parsed_results:
        raise ValueError("None of the Python files in the archive could be parsed successfully.")

    total_files = len(parsed_results)
    total_symbols = sum(len(p.symbols) for p in parsed_results)

    # 2. Atomic SQLite Transaction
    with get_db(db_path) as con:
        cur = con.cursor()
        try:
            # Insert repository record (initially inactive)
            cur.execute(
                """
                INSERT INTO repositories (id, name, uploaded_at, total_files, total_symbols, total_lines, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (repo_id, repo_name, uploaded_at, total_files, total_symbols, total_lines),
            )

            # Insert files and symbols
            for p in parsed_results:
                cur.execute(
                    """
                    INSERT INTO files (repository_id, path, language, size_bytes, line_count)
                    VALUES (?, ?, 'python', ?, ?)
                    """,
                    (repo_id, p.path, p.size_bytes, p.line_count),
                )
                file_id = cur.lastrowid

                for sym in p.symbols:
                    cur.execute(
                        """
                        INSERT INTO symbols (
                            file_id, repository_id, name, kind, parent_scope,
                            start_line, end_line, docstring, snippet
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            file_id,
                            repo_id,
                            sym.name,
                            sym.kind,
                            sym.parent_scope,
                            sym.start_line,
                            sym.end_line,
                            sym.docstring,
                            sym.snippet,
                        ),
                    )
                    symbol_id = cur.lastrowid

                    # Insert into FTS5 virtual table
                    cur.execute(
                        """
                        INSERT INTO code_search_fts (
                            symbol_name, file_path, parent_scope, docstring, content,
                            symbol_id, file_id, repository_id, start_line, end_line, kind
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sym.name,
                            sym.file_path,
                            sym.parent_scope or "",
                            sym.docstring or "",
                            sym.snippet,
                            symbol_id,
                            file_id,
                            repo_id,
                            sym.start_line,
                            sym.end_line,
                            sym.kind,
                        ),
                    )

            # Atomically replace previous active repository records
            # Cascade deletes files and symbols via FK, and explicitly purge FTS5 records
            cur.execute("DELETE FROM code_search_fts WHERE repository_id != ?", (repo_id,))
            cur.execute("DELETE FROM repositories WHERE id != ?", (repo_id,))
            cur.execute("UPDATE repositories SET is_active = 1 WHERE id = ?", (repo_id,))

            # Commit entire transaction
            con.commit()

        except Exception:
            con.rollback()
            raise

    return repo_id, total_files, total_symbols, total_lines, failed_files


def get_active_repository(db_path: Optional[Path] = None) -> Optional[dict]:
    """Retrieve the currently active repository record from SQLite."""
    with get_db(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, name, uploaded_at, total_files, total_symbols, total_lines
            FROM repositories
            WHERE is_active = 1
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)
