"""Unit tests for Python AST, JS/TS, and Markdown parsers."""

from src.backend.parsers.python_parser import parse_python_file
from src.backend.parsers.js_ts_parser import parse_js_ts_java_file
from src.backend.parsers.markdown_parser import parse_markdown_file


def test_python_ast_parsing_exact_lines():
    code = (
        '"""Module doc."""\n'
        'import os\n'
        '\n'
        'class AuthService:\n'
        '    """Auth service doc."""\n'
        '    def login(self, username, password):\n'
        '        """Perform login."""\n'
        '        return True\n'
        '\n'
        'def standalone_helper():\n'
        '    return 42\n'
    )

    chunks = parse_python_file("auth.py", code)
    # Check classes, methods, and functions found
    symbols = {c.symbol for c in chunks}
    assert "AuthService" in symbols
    assert "AuthService.login" in symbols
    assert "standalone_helper" in symbols

    # Check exact lines
    login_chunk = next(c for c in chunks if c.symbol == "AuthService.login")
    assert login_chunk.start_line == 6
    assert login_chunk.end_line == 8
    assert "Perform login" in login_chunk.docstring
    assert "os" in login_chunk.imports


def test_python_syntax_error_fallback():
    broken_code = "def invalid_syntax(:\n    pass\n"
    chunks = parse_python_file("broken.py", broken_code)
    assert len(chunks) > 0
    assert chunks[0].kind == "window"


def test_js_parser_functions_and_classes():
    js_code = (
        '/** Authenticate user */\n'
        'function loginUser(email, password) {\n'
        '    return fetch("/login");\n'
        '}\n'
        '\n'
        'const verifyToken = async (token) => {\n'
        '    return true;\n'
        '};\n'
    )

    chunks = parse_js_ts_java_file("auth.js", js_code, language="javascript")
    symbols = {c.symbol for c in chunks}
    assert "loginUser" in symbols
    assert "verifyToken" in symbols

    fn_chunk = next(c for c in chunks if c.symbol == "loginUser")
    assert "Authenticate user" in fn_chunk.docstring


def test_markdown_parser_headings():
    md = (
        '# Main Title\n'
        'Intro text\n'
        '## Section A\n'
        'Details for A\n'
        '## Section B\n'
        'Details for B\n'
    )

    chunks = parse_markdown_file("README.md", md)
    assert len(chunks) == 3
    symbols = [c.symbol for c in chunks]
    assert "Main Title" in symbols
    assert "Section A" in symbols
    assert "Section B" in symbols
