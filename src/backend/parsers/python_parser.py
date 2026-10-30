"""AST-based Python source code parser and chunker for NextGen Code Explorer."""

from __future__ import annotations

import ast
from typing import List, Optional
from src.backend.models import CodeChunk


def get_imports_from_module(tree: ast.AST) -> List[str]:
    """Collect imported module and symbol names from AST."""
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
    return imports


def split_large_chunk(
    chunk: CodeChunk,
    max_lines: int = 120,
    overlap: int = 20,
) -> List[CodeChunk]:
    """Split an oversized chunk into overlapping windows."""
    lines = chunk.code.splitlines()
    if len(lines) <= max_lines:
        return [chunk]

    sub_chunks: List[CodeChunk] = []
    start = 0
    sub_idx = 1
    total = len(lines)

    while start < total:
        end = min(start + max_lines, total)
        slice_code = "\n".join(lines[start:end])
        slice_start_line = chunk.start_line + start
        slice_end_line = chunk.start_line + end - 1

        sub_chunks.append(
            CodeChunk(
                id=f"{chunk.id}:w{sub_idx}",
                path=chunk.path,
                language=chunk.language,
                kind=chunk.kind,
                symbol=f"{chunk.symbol} (part {sub_idx})" if chunk.symbol else f"part {sub_idx}",
                parent=chunk.parent,
                start_line=slice_start_line,
                end_line=slice_end_line,
                code=slice_code,
                docstring=chunk.docstring if start == 0 else "",
                imports=chunk.imports,
            )
        )
        sub_idx += 1
        if end >= total:
            break
        start += max_lines - overlap

    return sub_chunks


def fallback_window_chunks(
    rel_path: str,
    code: str,
    language: str = "python",
    window_size: int = 80,
    overlap: int = 20,
) -> List[CodeChunk]:
    """Fallback chunker for syntax errors or unsupported formats."""
    lines = code.splitlines()
    if not lines:
        return []

    chunks: List[CodeChunk] = []
    total = len(lines)
    start = 0
    idx = 1

    while start < total:
        end = min(start + window_size, total)
        window_lines = lines[start:end]
        sub_code = "\n".join(window_lines)

        chunks.append(
            CodeChunk(
                id=f"{rel_path}:L{start + 1}-L{end}",
                path=rel_path,
                language=language,
                kind="window",
                symbol=f"{rel_path}:lines-{start + 1}-{end}",
                parent=None,
                start_line=start + 1,
                end_line=end,
                code=sub_code,
                docstring="",
                imports=[],
            )
        )
        idx += 1
        if end >= total:
            break
        start += window_size - overlap

    return chunks


def parse_python_file(
    rel_path: str,
    code: str,
    max_chunk_lines: int = 120,
) -> List[CodeChunk]:
    """Parse Python code using the standard library `ast` module.

    Extracts functions, classes, and methods with accurate line boundaries,
    docstrings, parent classes, and import statements.
    """
    if not code.strip():
        return []

    lines = code.splitlines()
    try:
        tree = ast.parse(code, filename=rel_path)
    except SyntaxError:
        # Fallback to sliding window chunks
        return fallback_window_chunks(rel_path, code, language="python")

    module_imports = get_imports_from_module(tree)
    chunks: List[CodeChunk] = []

    # Module-level docstring
    module_doc = ast.get_docstring(tree) or ""
    if module_doc:
        doc_lines = module_doc.splitlines()
        chunks.append(
            CodeChunk(
                id=f"{rel_path}:module_doc",
                path=rel_path,
                language="python",
                kind="doc",
                symbol="<module_doc>",
                parent=None,
                start_line=1,
                end_line=min(len(doc_lines) + 2, len(lines)),
                code=module_doc,
                docstring=module_doc,
                imports=module_imports,
            )
        )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_doc = ast.get_docstring(node) or ""
            start_line = node.lineno
            end_line = getattr(node, "end_lineno", start_line)
            fn_code = "\n".join(lines[start_line - 1 : end_line])

            base_chunk = CodeChunk(
                id=f"{rel_path}:{node.name}:L{start_line}-L{end_line}",
                path=rel_path,
                language="python",
                kind="function",
                symbol=node.name,
                parent=None,
                start_line=start_line,
                end_line=end_line,
                code=fn_code,
                docstring=fn_doc,
                imports=module_imports,
            )
            chunks.extend(split_large_chunk(base_chunk, max_chunk_lines))

        elif isinstance(node, ast.ClassDef):
            cls_doc = ast.get_docstring(node) or ""
            cls_start = node.lineno
            cls_end = getattr(node, "end_lineno", cls_start)
            cls_code = "\n".join(lines[cls_start - 1 : cls_end])

            # Class declaration chunk
            base_cls_chunk = CodeChunk(
                id=f"{rel_path}:{node.name}:L{cls_start}-L{cls_end}",
                path=rel_path,
                language="python",
                kind="class",
                symbol=node.name,
                parent=None,
                start_line=cls_start,
                end_line=cls_end,
                code=cls_code,
                docstring=cls_doc,
                imports=module_imports,
            )
            chunks.extend(split_large_chunk(base_cls_chunk, max_chunk_lines))

            # Extract methods separately for finer granularity
            for sub_node in node.body:
                if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    m_doc = ast.get_docstring(sub_node) or ""
                    m_start = sub_node.lineno
                    m_end = getattr(sub_node, "end_lineno", m_start)
                    m_code = "\n".join(lines[m_start - 1 : m_end])

                    method_chunk = CodeChunk(
                        id=f"{rel_path}:{node.name}.{sub_node.name}:L{m_start}-L{m_end}",
                        path=rel_path,
                        language="python",
                        kind="method",
                        symbol=f"{node.name}.{sub_node.name}",
                        parent=node.name,
                        start_line=m_start,
                        end_line=m_end,
                        code=m_code,
                        docstring=m_doc,
                        imports=module_imports,
                    )
                    chunks.extend(split_large_chunk(method_chunk, max_chunk_lines))

    # If no functions or classes were found (e.g. script / config file), create windowed chunks
    if not chunks:
        chunks = fallback_window_chunks(rel_path, code, language="python")

    return chunks
