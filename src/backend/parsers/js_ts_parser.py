"""Lightweight regex and brace-matching parser for JS/TS/Java source files."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from src.backend.models import CodeChunk
from src.backend.parsers.python_parser import fallback_window_chunks, split_large_chunk


def extract_imports_js_ts(code: str) -> List[str]:
    """Extract ES6 and CommonJS import module names."""
    imports: List[str] = []
    # import ... from 'module'
    for match in re.finditer(r"""import\s+(?:(?:[\w*\s{},]+)\s+from\s+)?['"]([^'"]+)['"]""", code):
        imports.append(match.group(1))
    # const ... = require('module')
    for match in re.finditer(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", code):
        imports.append(match.group(1))
    return imports


def find_matching_brace(code: str, start_brace_index: int) -> int:
    """Find the offset of the closing brace matching the opening brace at start_brace_index."""
    brace_depth = 0
    in_single_quote = False
    in_double_quote = False
    in_template_lit = False
    in_line_comment = False
    in_block_comment = False
    i = start_brace_index
    length = len(code)

    while i < length:
        ch = code[i]
        next_ch = code[i + 1] if i + 1 < length else ""

        # Handle comments
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and next_ch == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        # Handle strings
        if in_single_quote:
            if ch == "\\" and i + 1 < length:
                i += 2
                continue
            if ch == "'":
                in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            if ch == "\\" and i + 1 < length:
                i += 2
                continue
            if ch == '"':
                in_double_quote = False
            i += 1
            continue

        if in_template_lit:
            if ch == "\\" and i + 1 < length:
                i += 2
                continue
            if ch == "`":
                in_template_lit = False
            i += 1
            continue

        # Check comment starters
        if ch == "/" and next_ch == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and next_ch == "*":
            in_block_comment = True
            i += 2
            continue

        # Check string starters
        if ch == "'":
            in_single_quote = True
            i += 1
            continue
        if ch == '"':
            in_double_quote = True
            i += 1
            continue
        if ch == "`":
            in_template_lit = True
            i += 1
            continue

        # Brace counting
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0:
                return i

        i += 1

    return -1


def offset_to_line_no(line_offsets: List[int], char_offset: int) -> int:
    """Binary search or scan line offset index to get 1-based line number."""
    import bisect
    return bisect.bisect_right(line_offsets, char_offset)


def parse_js_ts_java_file(
    rel_path: str,
    code: str,
    language: str = "javascript",
    max_chunk_lines: int = 120,
) -> List[CodeChunk]:
    """Parse JS, TS, or Java code to extract classes, functions, and methods."""
    if not code.strip():
        return []

    lines = code.splitlines(keepends=True)
    line_offsets: List[int] = [0]
    for line in lines:
        line_offsets.append(line_offsets[-1] + len(line))

    imports = extract_imports_js_ts(code)
    chunks: List[CodeChunk] = []

    # Patterns for symbols with an opening brace
    patterns = [
        # Functions: function foo(...) { or async function foo(...) {
        (
            re.compile(r"""(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*\{"""),
            "function",
        ),
        # Arrow functions / function expressions: const foo = async (...) => { or const foo = function(...) {
        (
            re.compile(
                r"""(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>\s*\{"""
            ),
            "function",
        ),
        # Classes: class Foo { or class Foo extends Bar {
        (
            re.compile(r"""class\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+[a-zA-Z0-9_$.]+)?\s*\{"""),
            "class",
        ),
        # Java method definitions: public|private|protected static ... foo(...) {
        (
            re.compile(
                r"""(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?[\w<>\[\]]+\s+([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\{"""
            ),
            "method",
        ),
    ]

    matched_spans: List[Tuple[int, int, str, str]] = []

    for regex, kind in patterns:
        for m in regex.finditer(code):
            symbol = m.group(1)
            start_offset = m.start()
            brace_offset = code.find("{", start_offset)
            if brace_offset == -1:
                continue

            end_offset = find_matching_brace(code, brace_offset)
            if end_offset == -1:
                continue

            # Look backwards for JSDoc / docstring
            docstring = ""
            pre_text = code[:start_offset].rstrip()
            if pre_text.endswith("*/"):
                doc_start = pre_text.rfind("/**")
                if doc_start != -1:
                    docstring = pre_text[doc_start + 3 : -2].strip()

            matched_spans.append((start_offset, end_offset + 1, symbol, kind, docstring))

    # Sort spans by starting offset
    matched_spans.sort(key=lambda s: s[0])

    for start_off, end_off, symbol, kind, doc in matched_spans:
        start_line = offset_to_line_no(line_offsets, start_off)
        end_line = offset_to_line_no(line_offsets, end_off - 1)
        sub_code = code[start_off:end_off].strip()

        if not sub_code:
            continue

        chunk = CodeChunk(
            id=f"{rel_path}:{symbol}:L{start_line}-L{end_line}",
            path=rel_path,
            language=language,
            kind=kind,
            symbol=symbol,
            parent=None,
            start_line=start_line,
            end_line=end_line,
            code=sub_code,
            docstring=doc,
            imports=imports,
        )
        chunks.extend(split_large_chunk(chunk, max_chunk_lines))

    # Fallback if no structured blocks detected
    if not chunks:
        chunks = fallback_window_chunks(rel_path, code, language=language)

    return chunks
