"""Markdown and documentation chunker for NextGen Code Explorer."""

from __future__ import annotations

import re
from typing import List
from src.backend.models import CodeChunk
from src.backend.parsers.python_parser import split_large_chunk


def parse_markdown_file(
    rel_path: str,
    content: str,
    max_chunk_lines: int = 120,
) -> List[CodeChunk]:
    """Split Markdown/README documents into structured section chunks by heading."""
    if not content.strip():
        return []

    lines = content.splitlines()
    heading_regex = re.compile(r"^(#{1,6})\s+(.+)$")
    sections: List[dict] = []
    current_title = "Introduction"
    current_start = 1
    current_lines: List[str] = []

    for idx, line in enumerate(lines):
        line_no = idx + 1
        m = heading_regex.match(line)
        if m:
            if current_lines:
                sections.append({
                    "title": current_title,
                    "start": current_start,
                    "end": line_no - 1,
                    "lines": current_lines,
                })
            current_title = m.group(2).strip()
            current_start = line_no
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "title": current_title,
            "start": current_start,
            "end": len(lines),
            "lines": current_lines,
        })

    chunks: List[CodeChunk] = []
    for s_idx, sec in enumerate(sections, 1):
        code_text = "\n".join(sec["lines"]).strip()
        if not code_text:
            continue

        chunk = CodeChunk(
            id=f"{rel_path}:doc{s_idx}:L{sec['start']}-L{sec['end']}",
            path=rel_path,
            language="markdown",
            kind="doc",
            symbol=sec["title"],
            parent=None,
            start_line=sec["start"],
            end_line=sec["end"],
            code=code_text,
            docstring=code_text,
            imports=[],
        )
        chunks.extend(split_large_chunk(chunk, max_chunk_lines))

    return chunks
