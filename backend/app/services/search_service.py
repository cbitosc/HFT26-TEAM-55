"""SQLite FTS5 Full-Text Code Search Service.

Safely compiles natural-language code queries into parameterized FTS5 expressions,
applies BM25 ranking, and validates references against active relational records.
"""

import logging
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from app.db.database import get_db, DB_PATH

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    """Raised when an error occurs during FTS5 code search execution."""
    pass


def sanitize_fts5_query(query: str) -> Optional[str]:
    """Sanitize user search query into a safe FTS5 prefix expression.

    Extracts word tokens and formats them as prefix tokens ('"token"*')
    to prevent FTS5 syntax errors and injection.
    """
    if not query:
        return None

    # Extract alphanumeric words and common programming identifiers
    words = re.findall(r"[A-Za-z0-9_]+", query)
    if not words:
        return None

    # Filter very short meaningless single characters except 'a' or 'i'
    clean_words = [w for w in words if len(w) > 1 or w.isalnum()]
    if not clean_words:
        return None

    # Create prefix query tokens
    # e.g., 'auth user' -> '"auth"* OR "user"*'
    return " OR ".join(f'"{w}"*' for w in clean_words)


def search_codebase(
    query: str,
    limit: int = 25,
    db_path: Optional[Path] = None,
) -> Dict:
    """Execute full-text search across indexed code symbols, paths, and snippets.

    Returns:
        Dict containing query, total_matches, repository_name, and results list.
    """
    resolved_limit = limit.default if hasattr(limit, "default") and not isinstance(limit, int) else int(limit)
    fts_expression = sanitize_fts5_query(query)
    if not fts_expression:
        return {
            "query": query,
            "total_matches": 0,
            "repository_name": None,
            "results": [],
        }

    with get_db(db_path) as con:
        cur = con.cursor()

        # Check active repository
        try:
            cur.execute(
                """
                SELECT id, name FROM repositories WHERE is_active = 1 LIMIT 1
                """
            )
            active_repo = cur.fetchone()
        except sqlite3.OperationalError as exc:
            logger.error("Database error retrieving active repository: %s", exc)
            raise SearchServiceError(f"Database error checking active repository: {exc}") from exc

        if not active_repo:
            return {
                "query": query,
                "total_matches": 0,
                "repository_name": None,
                "results": [],
            }

        repo_id = active_repo["id"]
        repo_name = active_repo["name"]

        # Parameterized FTS5 Search using code_search_fts consistently in MATCH, bm25(), and snippet()
        sql = """
            SELECT 
                code_search_fts.symbol_id,
                code_search_fts.file_id,
                code_search_fts.symbol_name,
                code_search_fts.file_path,
                code_search_fts.parent_scope,
                code_search_fts.kind,
                code_search_fts.start_line,
                code_search_fts.end_line,
                code_search_fts.docstring,
                code_search_fts.content AS snippet,
                snippet(code_search_fts, 4, '<mark>', '</mark>', '...', 25) AS highlight,
                bm25(code_search_fts, 5.0, 3.0, 2.0, 1.0, 1.5) AS rank_score
            FROM code_search_fts
            JOIN symbols ON symbols.id = CAST(code_search_fts.symbol_id AS INTEGER)
            WHERE code_search_fts.repository_id = ? AND code_search_fts MATCH ?
            ORDER BY rank_score ASC
            LIMIT ?
        """

        try:
            cur.execute(sql, (repo_id, fts_expression, limit))
            rows = cur.fetchall()
        except sqlite3.OperationalError as exc:
            logger.error(
                "SQLite FTS5 query execution failed for query '%s' (expression: '%s'): %s",
                query,
                fts_expression,
                exc,
            )
            raise SearchServiceError(f"FTS5 query execution failed: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected error executing database search for query '%s': %s", query, exc)
            raise SearchServiceError(f"Unexpected error executing search: {exc}") from exc

        results: List[Dict] = []
        for r in rows:
            # Format clean snippet highlight if FTS5 highlight didn't hit content
            highlight_snippet = r["highlight"] if r["highlight"] else r["snippet"]

            results.append(
                {
                    "symbol_id": int(r["symbol_id"]),
                    "file_id": int(r["file_id"]),
                    "name": r["symbol_name"],
                    "file_path": r["file_path"],
                    "parent_scope": r["parent_scope"] or None,
                    "kind": r["kind"],
                    "start_line": int(r["start_line"]),
                    "end_line": int(r["end_line"]),
                    "docstring": r["docstring"] or None,
                    "snippet": r["snippet"],
                    "highlight": highlight_snippet,
                    "rank": round(float(r["rank_score"]), 3),
                }
            )

        return {
            "query": query,
            "total_matches": len(results),
            "repository_name": repo_name,
            "results": results,
        }
