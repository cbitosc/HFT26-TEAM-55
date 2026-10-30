"""Parsers package for extracting code structures and chunks."""

from __future__ import annotations

from pathlib import Path
from typing import List
from src.backend.models import CodeChunk
from src.backend.parsers.python_parser import parse_python_file, fallback_window_chunks
from src.backend.parsers.js_ts_parser import parse_js_ts_java_file
from src.backend.parsers.markdown_parser import parse_markdown_file

LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".sh": "bash",
    ".txt": "text",
}


def parse_source_file(rel_path: str, abs_path: Path) -> List[CodeChunk]:
    """Read a source file and extract CodeChunks using language-specific parsers."""
    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    ext = abs_path.suffix.lower()
    language = LANG_MAP.get(ext, "text")

    if ext == ".py":
        return parse_python_file(rel_path, content)
    elif ext in (".js", ".jsx", ".mjs", ".cjs"):
        return parse_js_ts_java_file(rel_path, content, language="javascript")
    elif ext in (".ts", ".tsx"):
        return parse_js_ts_java_file(rel_path, content, language="typescript")
    elif ext == ".java":
        return parse_js_ts_java_file(rel_path, content, language="java")
    elif ext in (".md", ".markdown"):
        return parse_markdown_file(rel_path, content)
    else:
        return fallback_window_chunks(rel_path, content, language=language)
