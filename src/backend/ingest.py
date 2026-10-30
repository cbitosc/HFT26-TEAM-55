"""Safe repository ingestion and archive extraction for NextGen Code Explorer.

Guarantees zip-slip prevention, symlink rejection, resource bounds,
single top-level folder flattening, and deterministic file filtering.
"""

from __future__ import annotations

import io
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.backend import config


class IngestionError(Exception):
    """Raised when an uploaded archive fails validation or safety constraints."""
    pass


def is_symlink(info: zipfile.ZipInfo) -> bool:
    """Check if a ZipInfo entry is marked as a symbolic link."""
    # UNIX file mode is stored in the upper 16 bits of external_attr
    mode = info.external_attr >> 16
    return (mode & 0o170000) == 0o120000


def validate_zip_safety(
    zf: zipfile.ZipFile,
    max_uncompressed_bytes: int = config.MAX_UNCOMPRESSED_SIZE_MB * 1024 * 1024,
    max_files: int = config.MAX_FILE_COUNT,
    max_compression_ratio: float = config.MAX_COMPRESSION_RATIO,
) -> None:
    """Audit zip archive entries for Zip-Slip, zip bombs, and symlinks before extraction."""
    total_uncompressed = 0
    total_compressed = 0
    file_count = 0

    for info in zf.infolist():
        # Reject absolute paths or paths with directory traversal
        filename = info.filename
        if filename.startswith("/") or filename.startswith("\\") or ".." in filename.split("/"):
            raise IngestionError(f"Unsafe path detected in archive: '{filename}' (Zip-Slip attempt)")

        # Disallow symlinks
        if is_symlink(info):
            raise IngestionError(f"Symbolic links are not permitted in archive: '{filename}'")

        file_count += 1
        if file_count > max_files:
            raise IngestionError(f"Archive exceeds maximum allowed file count ({max_files})")

        total_uncompressed += info.file_size
        total_compressed += info.compress_size

        if total_uncompressed > max_uncompressed_bytes:
            raise IngestionError(
                f"Archive uncompressed size exceeds limit of {max_uncompressed_bytes // (1024*1024)} MB"
            )

    # Check compression ratio for zip bomb defense
    if total_compressed > 0:
        ratio = total_uncompressed / total_compressed
        if ratio > max_compression_ratio and total_uncompressed > 5 * 1024 * 1024:
            raise IngestionError(
                f"Suspicious compression ratio ({ratio:.1f}:1). Maximum allowed is {max_compression_ratio}:1"
            )


def extract_zip_safely(
    zip_bytes_or_path: bytes | Path | str,
    target_dir: Path,
) -> Path:
    """Safely extract a ZIP archive into target_dir.

    Flattens single top-level wrapper directory if present.
    """
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(zip_bytes_or_path, (str, Path)):
        zf = zipfile.ZipFile(zip_bytes_or_path, "r")
    else:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes_or_path), "r")

    try:
        validate_zip_safety(zf)

        for info in zf.infolist():
            # Skip directories; we create them as needed
            if info.is_dir():
                continue

            # Compute normalized target file path
            dest_path = (target_dir / info.filename).resolve()

            # Strict path containment check
            try:
                dest_path.relative_to(target_dir)
            except ValueError:
                raise IngestionError(f"Path traversal detected: {info.filename}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    finally:
        zf.close()

    # Flatten single root folder if repository was packaged inside one root folder
    strip_single_root_folder(target_dir)
    return target_dir


def strip_single_root_folder(directory: Path) -> None:
    """If all contents in directory reside under a single subfolder, hoist them up one level."""
    entries = [p for p in directory.iterdir() if p.name not in (".git", "__MACOSX")]
    if len(entries) == 1 and entries[0].is_dir():
        single_dir = entries[0]
        temp_dir = directory.parent / f"_temp_flatten_{uuid.uuid4().hex}"
        shutil.move(str(single_dir), str(temp_dir))

        # Move children of temp_dir into directory
        for item in temp_dir.iterdir():
            shutil.move(str(item), str(directory / item.name))

        # Cleanup temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def is_binary_file(file_path: Path) -> bool:
    """Check if file contains null bytes within its first 8 KB."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except Exception:
        return True


def should_index_file(
    rel_path: Path,
    abs_path: Path,
    max_file_size: int = config.MAX_SINGLE_FILE_BYTES,
) -> Tuple[bool, Optional[str]]:
    """Determine whether a file should be indexed or skipped.

    Returns:
        (should_index, skip_reason)
    """
    parts = rel_path.parts

    # Excluded directories
    for part in parts[:-1]:
        if part in config.EXCLUDED_DIRS:
            return False, f"Directory '{part}' is excluded"

    filename = rel_path.name
    lower_name = filename.lower()

    # Excluded filenames (lock files, etc.)
    if lower_name in config.EXCLUDED_FILENAMES:
        return False, "Lock file excluded"

    # Minified files and source maps
    if lower_name.endswith(".min.js") or lower_name.endswith(".min.css") or lower_name.endswith(".map"):
        return False, "Minified code or sourcemap excluded"

    # Excluded extensions
    suffix = rel_path.suffix.lower()
    if suffix in config.EXCLUDED_EXTENSIONS:
        return False, f"File extension '{suffix}' excluded"

    # Check size
    try:
        size = abs_path.stat().st_size
        if size == 0:
            return False, "Empty file"
        if size > max_file_size:
            return False, f"Exceeds size limit ({size / 1024:.1f} KB > {max_file_size // 1024} KB)"
    except Exception as e:
        return False, f"Cannot stat file: {e}"

    # Check for binary content
    if is_binary_file(abs_path):
        return False, "Binary file detected"

    return True, None


def scan_repository(
    repo_dir: Path,
    max_file_size: int = config.MAX_SINGLE_FILE_BYTES,
) -> Tuple[List[Tuple[str, Path]], Dict[str, int]]:
    """Scan a repository folder, returning accepted relative files and a breakdown of skipped files."""
    repo_dir = repo_dir.resolve()
    accepted_files: List[Tuple[str, Path]] = []
    skipped_stats: Dict[str, int] = {}

    for root, dirs, files in os.walk(repo_dir):
        # Prune excluded directories in-place to avoid traversing them
        dirs[:] = [d for d in dirs if d not in config.EXCLUDED_DIRS]

        for file in files:
            abs_path = Path(root) / file
            try:
                rel_path = abs_path.relative_to(repo_dir)
            except ValueError:
                continue

            normalized_rel = str(rel_path).replace("\\", "/")
            admitted, reason = should_index_file(rel_path, abs_path, max_file_size)

            if admitted:
                accepted_files.append((normalized_rel, abs_path))
            else:
                category = reason.split(":")[0] if reason else "other"
                skipped_stats[category] = skipped_stats.get(category, 0) + 1

    return accepted_files, skipped_stats
