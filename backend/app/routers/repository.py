"""Repository ingestion and status API routes."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.services.zip_validator import validate_and_extract_zip, ZipValidationError
from app.services.indexer import index_repository_contents, get_active_repository

router = APIRouter(prefix="/repository", tags=["repository"])


@router.post("/upload")
async def upload_repository_archive(file: UploadFile = File(...)):
    """Upload, validate, parse, and index a ZIP archive into SQLite FTS5."""
    if not file.filename or not file.filename.lower().endswith((".zip", ".tar.gz", ".tar")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive (.zip)",
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded archive: {exc}",
        )

    # 1. Validate ZIP and extract Python files safely in memory
    try:
        repo_name, python_files, skipped_files, warnings = validate_and_extract_zip(content)
    except ZipValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # 2. Parse AST symbols and atomically index into SQLite FTS5
    try:
        repo_id, total_files, total_symbols, total_lines, failed_files = index_repository_contents(
            repo_name=repo_name,
            python_files=python_files,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {exc}",
        )

    return {
        "status": "indexed",
        "repository_id": repo_id,
        "repo_name": repo_name,
        "total_files": total_files,
        "total_symbols": total_symbols,
        "total_lines": total_lines,
        "skipped_files_count": len(skipped_files),
        "excluded_files_count": len(skipped_files),
        "skipped_files_sample": skipped_files[:20],
        "failed_files": [{"path": f.path, "error": f.error, "line": f.line} for f in failed_files],
    }


@router.get("/status")
def get_repository_status():
    """Retrieve the current active indexed repository metadata."""
    active_repo = get_active_repository()
    if not active_repo:
        return {
            "has_repository": False,
            "repository": None,
        }

    return {
        "has_repository": True,
        "repository": active_repo,
    }
