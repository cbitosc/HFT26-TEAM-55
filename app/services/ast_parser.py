"""Fault-tolerant Python AST Visitor & Symbol Extractor.

Extracts classes, methods, functions, and nested definitions with accurate line ranges,
docstrings, and relevant source snippets. Handles syntax errors per file without aborting the batch.
"""

import ast
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ExtractedSymbol:
    """Represents a code symbol extracted from an AST."""
    name: str
    kind: str           # 'function', 'async_function', 'class', 'method', 'async_method'
    file_path: str
    parent_scope: Optional[str]
    start_line: int
    end_line: int
    docstring: Optional[str]
    snippet: str


@dataclass
class ParsedFileResult:
    """Result of parsing a single Python source file."""
    path: str
    size_bytes: int
    line_count: int
    symbols: List[ExtractedSymbol] = field(default_factory=list)


@dataclass
class FailedFileResult:
    """Information regarding a file that failed syntax parsing."""
    path: str
    error: str
    line: Optional[int] = None


class ScopeSymbolVisitor(ast.NodeVisitor):
    """AST visitor that tracks scope to preserve classes, methods, and nested functions."""

    def __init__(self, file_path: str, source_lines: List[str]):
        self.file_path = file_path
        self.source_lines = source_lines
        self.symbols: List[ExtractedSymbol] = []
        self.scope_stack: List[Tuple[str, str]] = []  # List of (name, type)

    def _extract_snippet(self, start_line: int, end_line: int, max_lines: int = 40) -> str:
        """Extract exact source snippet bounded to a reasonable display length."""
        if start_line < 1:
            start_line = 1
        # 1-indexed to 0-indexed
        lines = self.source_lines[start_line - 1 : min(end_line, start_line + max_lines - 1)]
        return "\n".join(lines)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        parent_scope = self.scope_stack[-1][0] if self.scope_stack else None
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", node.lineno) or node.lineno
        docstring = ast.get_docstring(node)
        snippet = self._extract_snippet(start_line, end_line)

        self.symbols.append(
            ExtractedSymbol(
                name=node.name,
                kind="class",
                file_path=self.file_path,
                parent_scope=parent_scope,
                start_line=start_line,
                end_line=end_line,
                docstring=docstring,
                snippet=snippet,
            )
        )

        self.scope_stack.append((node.name, "class"))
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node, is_async=True)

    def _record_function(self, node: ast.AST, is_async: bool) -> None:
        parent_name = None
        parent_type = None
        if self.scope_stack:
            parent_name, parent_type = self.scope_stack[-1]

        # Determine symbol kind
        if parent_type == "class":
            kind = "async_method" if is_async else "method"
        else:
            kind = "async_function" if is_async else "function"

        start_line = node.lineno
        end_line = getattr(node, "end_lineno", node.lineno) or node.lineno
        docstring = ast.get_docstring(node)
        snippet = self._extract_snippet(start_line, end_line)

        self.symbols.append(
            ExtractedSymbol(
                name=node.name,
                kind=kind,
                file_path=self.file_path,
                parent_scope=parent_name,
                start_line=start_line,
                end_line=end_line,
                docstring=docstring,
                snippet=snippet,
            )
        )

        self.scope_stack.append((node.name, "function"))
        self.generic_visit(node)
        self.scope_stack.pop()


def parse_python_file(file_path: str, source_code: str) -> Tuple[Optional[ParsedFileResult], Optional[FailedFileResult]]:
    """Parse a single Python file into symbols or return failure info."""
    source_lines = source_code.splitlines()
    line_count = len(source_lines)
    size_bytes = len(source_code.encode("utf-8"))

    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError as err:
        return None, FailedFileResult(
            path=file_path,
            error=f"SyntaxError: {err.msg}",
            line=err.lineno,
        )
    except Exception as exc:
        return None, FailedFileResult(
            path=file_path,
            error=str(exc),
        )

    visitor = ScopeSymbolVisitor(file_path, source_lines)
    visitor.visit(tree)

    return (
        ParsedFileResult(
            path=file_path,
            size_bytes=size_bytes,
            line_count=line_count,
            symbols=visitor.symbols,
        ),
        None,
    )
