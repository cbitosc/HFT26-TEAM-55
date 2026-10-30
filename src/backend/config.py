"""Application configuration and default limits."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Set
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data" / "sessions")))
SAMPLE_REPO_DIR = BASE_DIR / "tests" / "sample_repo"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Ingestion limits
MAX_ZIP_SIZE_MB = int(os.getenv("MAX_ZIP_SIZE_MB", "50"))
MAX_UNCOMPRESSED_SIZE_MB = int(os.getenv("MAX_UNCOMPRESSED_SIZE_MB", "200"))
MAX_FILE_COUNT = int(os.getenv("MAX_FILE_COUNT", "5000"))
MAX_SINGLE_FILE_BYTES = int(os.getenv("MAX_SINGLE_FILE_BYTES", "204800"))  # 200 KB
MAX_COMPRESSION_RATIO = float(os.getenv("MAX_COMPRESSION_RATIO", "100.0"))
ENABLE_LOCAL_PATH = os.getenv("ENABLE_LOCAL_PATH", "0").lower() in ("1", "true", "yes")

# Excluded directories
EXCLUDED_DIRS: Set[str] = {
    ".git",
    ".github",
    ".svn",
    ".hg",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "vendor",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    "eggs",
    ".eggs",
}

# Excluded binary and archive file extensions
EXCLUDED_EXTENSIONS: Set[str] = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".img",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz",
    ".whl", ".pyc", ".pyo", ".pyd", ".class", ".jar",
    ".db", ".sqlite", ".sqlite3", ".o", ".a", ".lib",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}

# Excluded full filenames (lock files, minified suffixes)
EXCLUDED_FILENAMES: Set[str] = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    "pipfile.lock",
    "composer.lock",
}

# BM25 & Retrieval Parameters
BM25_K1 = float(os.getenv("BM25_K1", "1.5"))
BM25_B = float(os.getenv("BM25_B", "0.75"))

WEIGHT_SYMBOL = float(os.getenv("WEIGHT_SYMBOL", "3.0"))
WEIGHT_PATH = float(os.getenv("WEIGHT_PATH", "2.0"))
WEIGHT_DOCSTRING = float(os.getenv("WEIGHT_DOCSTRING", "1.5"))
WEIGHT_CODE = float(os.getenv("WEIGHT_CODE", "1.0"))

BOOST_EXACT_SYMBOL = 4.0
BOOST_PATH_MATCH = 2.5
BOOST_DOCS_FOR_HELP = 2.0
RRF_K = int(os.getenv("RRF_K", "60"))

# Featherless AI Settings
FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY", "")
FEATHERLESS_MODEL = os.getenv("FEATHERLESS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
FEATHERLESS_BASE_URL = os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
APP_TITLE = "NextGen Code Explorer"
