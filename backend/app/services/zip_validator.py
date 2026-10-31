"""Defensive ZIP Archive Validator.

Enforces strict security checks against path traversal, symlinks, zip bombs,
encryption, corrupt entries, and excessive archive sizes without writing to disk.
"""

import io
import posixpath
import zipfile
from typing import Dict, List, Optional, Tuple


class ZipValidationError(ValueError):
    """Raised when an uploaded ZIP archive violates safety or limit rules."""
    pass


# Security & Size Limits
MAX_ARCHIVE_SIZE_BYTES = 20 * 1024 * 1024       # 20 MiB
MAX_EXPANDED_SIZE_BYTES = 100 * 1024 * 1024     # 100 MiB
MAX_ARCHIVE_ENTRIES = 10_000                     # 10,000 total items
MAX_ELIGIBLE_SOURCE_FILES = 1_000               # 1,000 Python source files
MAX_PER_FILE_SIZE_BYTES = 256 * 1024            # 256 KiB per Python source file

# Directories to exclude from indexing (common build artifacts, dependencies, virtual environments, caches)
EXCLUDED_DIR_NAMES = {
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    ".yarn",
    ".cache",
    ".turbo",
    ".out",
    "out",
    ".egg-info",
}

# Generated files, compiled binaries, and non-source artifacts to exclude
EXCLUDED_FILE_EXTENSIONS = {
    # Compiled Python bytecode
    ".pyc",
    ".pyo",
    ".pyd",
    # Source maps
    ".map",
    # Compiled libraries, binaries, and executables
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".whl",
    ".egg",
    ".o",
    ".a",
    ".obj",
    # Compressed sub-archives
    ".tar",
    ".gz",
    ".zip",
    ".7z",
    ".rar",
    # WebAssembly
    ".wasm",
    # Dependency lock files
    ".lock",
}


def is_excluded_or_non_python(rel_path: str) -> Tuple[bool, Optional[str]]:
    """Determine if a repository path should be excluded from Python indexing.

    Identifies generated build directories, vendor packages, caches, compiled binaries,
    minified bundles, and non-Python files.

    Returns:
        Tuple of (is_excluded: bool, reason: Optional[str])
    """
    parts = rel_path.split("/")
    filename = parts[-1].lower() if parts else ""

    # 1. Directory-level exclusions (e.g. node_modules, dist, build, .venv, etc.)
    for part in parts[:-1]:
        part_lower = part.lower()
        if part_lower in EXCLUDED_DIR_NAMES or part_lower.startswith("."):
            return True, f"directory '{part}' is excluded"

    # 2. Hidden files (e.g. .DS_Store, .gitignore, .env)
    if filename.startswith("."):
        return True, "hidden file"

    # 3. Explicit excluded extensions (compiled binaries, bytecode, source maps)
    for ext in EXCLUDED_FILE_EXTENSIONS:
        if filename.endswith(ext):
            return True, f"excluded extension '{ext}'"

    # 4. Common minified / bundled asset patterns (e.g. *.min.js, *.bundle.js, *.chunk.js)
    if (
        filename.endswith(".min.js")
        or filename.endswith(".min.css")
        or filename.endswith(".bundle.js")
        or filename.endswith(".bundle.css")
        or filename.endswith(".chunk.js")
        or filename.endswith(".chunk.css")
    ):
        return True, "minified/bundled asset"

    # 5. Non-Python source files (CodeCompass indexes Python source code exclusively)
    if not filename.endswith(".py"):
        return True, "non-Python file"

    return False, None


def validate_and_extract_zip(
    zip_bytes: bytes,
) -> Tuple[str, Dict[str, str], List[str], List[str]]:
    """Inspect and extract Python files from a ZIP archive purely in memory.

    Args:
        zip_bytes: Raw bytes of the uploaded ZIP file.

    Returns:
        Tuple containing:
            - repo_name: Detected or sanitized repository name
            - python_files: Mapping of repo-relative path to file content string
            - skipped_files: List of skipped non-Python or excluded file paths
            - member_warnings: List of non-fatal warnings
    """
    # 1. Archive size check
    if len(zip_bytes) > MAX_ARCHIVE_SIZE_BYTES:
        raise ZipValidationError(
            f"Archive size exceeds 20 MiB limit (received {len(zip_bytes) / (1024 * 1024):.2f} MiB)"
        )

    if not zipfile.is_zipfile(io.BytesIO(zip_bytes)):
        raise ZipValidationError("Uploaded file is not a valid ZIP archive or is corrupt.")

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as exc:
        raise ZipValidationError(f"Failed to open ZIP archive: {exc}")

    with zf:
        infolist = zf.infolist()

        # 2. Maximum archive entries
        if len(infolist) > MAX_ARCHIVE_ENTRIES:
            raise ZipValidationError(
                f"Archive contains too many entries ({len(infolist)} > {MAX_ARCHIVE_ENTRIES})"
            )

        # Pre-flight inspection on all member headers before reading data
        seen_normalized_paths = set()
        cumulative_decompressed_size = 0
        eligible_members: List[Tuple[zipfile.ZipInfo, str]] = []
        skipped_files: List[str] = []
        member_warnings: List[str] = []

        # Find potential common root directory (e.g. repo-main/ generated by GitHub)
        all_names = [info.filename for info in infolist if not info.is_dir()]
        common_root = ""
        if all_names:
            parts = [p.split("/") for p in all_names]
            first_dirs = {p[0] for p in parts if len(p) > 1}
            if len(first_dirs) == 1:
                common_root = list(first_dirs)[0] + "/"

        for info in infolist:
            filename = info.filename

            # Skip directory entries
            if info.is_dir() or filename.endswith("/"):
                continue

            # Check 1: Encrypted entries
            if info.flag_bits & 0x1:
                raise ZipValidationError(f"Encrypted archives are not supported (entry: {filename})")

            # Check 2: Path traversal, drive letters, null bytes, absolute paths
            if "\0" in filename:
                raise ZipValidationError("Null byte detected in file path")
            if filename.startswith("/") or filename.startswith("\\"):
                raise ZipValidationError(f"Absolute path detected: {filename}")
            if ":" in filename:  # Windows drive letter attempt
                raise ZipValidationError(f"Path contains invalid drive letter: {filename}")
            if ".." in filename.split("/") or ".." in filename.split("\\"):
                raise ZipValidationError(f"Path traversal sequence detected: {filename}")

            # Normalize path
            norm = posixpath.normpath(filename.replace("\\", "/"))
            if norm.startswith("../") or norm.startswith("/") or norm == ".":
                raise ZipValidationError(f"Illegal normalized path: {filename}")

            # Check 3: Duplicate entries
            if norm in seen_normalized_paths:
                raise ZipValidationError(f"Duplicate entry path detected: {norm}")
            seen_normalized_paths.add(norm)

            # Check 4: Symlinks (POSIX external attributes)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ZipValidationError(f"Symlinks are prohibited in archives: {filename}")

            # Check 5: Cumulative declared size & compression ratio across all members
            cumulative_decompressed_size += info.file_size
            if cumulative_decompressed_size > MAX_EXPANDED_SIZE_BYTES:
                raise ZipValidationError("Decompressed content exceeds 100 MiB limit (decompression bomb protection)")

            if info.compress_size > 0 and (info.file_size / info.compress_size) > 100 and info.file_size > 64 * 1024:
                raise ZipValidationError(f"Suspicious compression ratio on member: {filename}")

            # Strip common root folder if present to normalize repo-relative path
            rel_path = norm
            if common_root and rel_path.startswith(common_root):
                rel_path = rel_path[len(common_root):]

            # Check 6: Intelligent exclusion of generated directories, build artifacts, bundles, and non-Python files
            is_excluded, reason = is_excluded_or_non_python(rel_path)
            if is_excluded:
                skipped_files.append(rel_path)
                continue

            # Check 7: Eligible Python source file size limit (enforced strictly on Python source files)
            if info.file_size > MAX_PER_FILE_SIZE_BYTES:
                raise ZipValidationError(
                    f"Python source file '{rel_path}' exceeds maximum allowed size of 256 KiB ({info.file_size / 1024:.1f} KiB)"
                )

            eligible_members.append((info, rel_path))

        # Check 7: Eligible source file count
        if len(eligible_members) > MAX_ELIGIBLE_SOURCE_FILES:
            raise ZipValidationError(
                f"Too many Python source files ({len(eligible_members)} > {MAX_ELIGIBLE_SOURCE_FILES})"
            )

        if not eligible_members:
            raise ZipValidationError("No valid Python source files (.py) found in the uploaded archive.")

        # Phase 2: Stream read with CRC verification and strict size counter
        python_files: Dict[str, str] = {}
        actual_decompressed_bytes = 0

        for info, rel_path in eligible_members:
            try:
                with zf.open(info) as f:
                    content_bytes = bytearray()
                    while True:
                        chunk = f.read(16 * 1024)
                        if not chunk:
                            break
                        content_bytes.extend(chunk)
                        actual_decompressed_bytes += len(chunk)
                        if len(content_bytes) > MAX_PER_FILE_SIZE_BYTES:
                            raise ZipValidationError(f"File '{rel_path}' exceeded 256 KiB during decompression")
                        if actual_decompressed_bytes > MAX_EXPANDED_SIZE_BYTES:
                            raise ZipValidationError("Exceeded cumulative 100 MiB limit during decompression")

                    # Decode file with utf-8 / fallback to latin-1
                    try:
                        content_str = content_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        content_str = content_bytes.decode("latin-1", errors="replace")

                    python_files[rel_path] = content_str

            except zipfile.BadZipFile as exc:
                raise ZipValidationError(f"Corrupt entry or CRC error reading '{rel_path}': {exc}")
            except Exception as exc:
                if isinstance(exc, ZipValidationError):
                    raise
                raise ZipValidationError(f"Failed to decompress '{rel_path}': {exc}")

        # Derive repository name
        repo_name = common_root.rstrip("/") if common_root else "codebase"

        return repo_name, python_files, skipped_files, member_warnings
