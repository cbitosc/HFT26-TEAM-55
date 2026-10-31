"""Search API routes for CodeCompass FTS5 code search."""

import logging
from fastapi import APIRouter, HTTPException, Query, status
from app.services.search_service import search_codebase, SearchServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
@router.get("/")
def search_code(
    q: str = Query("", description="Search query string"),
    limit: int = Query(25, ge=1, le=100, description="Max search results"),
):
    """Execute SQLite FTS5 BM25 search across indexed code symbols, files, and snippets."""
    # Ensure raw parameters work both through FastAPI DI and direct Python invocation
    query_str = q.default if hasattr(q, "default") and not isinstance(q, str) else str(q)
    limit_int = limit.default if hasattr(limit, "default") and not isinstance(limit, int) else int(limit)
    try:
        return search_codebase(query=query_str, limit=limit_int)
    except SearchServiceError as exc:
        logger.error("Search service error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error executing code search for query '%s': %s", q, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while executing search: {exc}",
        )
