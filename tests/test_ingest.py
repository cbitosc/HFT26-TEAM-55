"""Unit tests for archive ingestion and file filtering safety."""

import io
import zipfile
import pytest
from pathlib import Path

from src.backend.ingest import (
    IngestionError,
    extract_zip_safely,
    is_binary_file,
    should_index_file,
    validate_zip_safety,
)


def test_zip_slip_rejection():
    # Construct an in-memory zip file attempting directory traversal
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0:")
    buf.seek(0)

    with pytest.raises(IngestionError, match="Unsafe path detected"):
        with zipfile.ZipFile(buf, "r") as zf:
            validate_zip_safety(zf)


def test_file_filtering_exclusions(tmp_path):
    # Excluded directories
    rel_p1 = Path("node_modules/express/index.js")
    abs_p1 = tmp_path / rel_p1
    abs_p1.parent.mkdir(parents=True, exist_ok=True)
    abs_p1.write_text("console.log(1);")
    admitted1, reason1 = should_index_file(rel_p1, abs_p1)
    assert not admitted1
    assert "node_modules" in reason1

    # Lock file
    rel_p2 = Path("package-lock.json")
    abs_p2 = tmp_path / rel_p2
    abs_p2.write_text('{"name": "test"}')
    admitted2, reason2 = should_index_file(rel_p2, abs_p2)
    assert not admitted2
    assert "Lock file" in reason2

    # Minified js
    rel_p3 = Path("bundle.min.js")
    abs_p3 = tmp_path / rel_p3
    abs_p3.write_text("var a=1;")
    admitted3, reason3 = should_index_file(rel_p3, abs_p3)
    assert not admitted3
    assert "Minified" in reason3

    # Oversized file
    rel_p4 = Path("huge.py")
    abs_p4 = tmp_path / rel_p4
    abs_p4.write_text("x = 1\n" * 100000)
    admitted4, reason4 = should_index_file(rel_p4, abs_p4, max_file_size=5000)
    assert not admitted4
    assert "Exceeds size limit" in reason4

    # Legitimate python file
    rel_p5 = Path("src/auth.py")
    abs_p5 = tmp_path / rel_p5
    abs_p5.parent.mkdir(parents=True, exist_ok=True)
    abs_p5.write_text("def login(): pass")
    admitted5, reason5 = should_index_file(rel_p5, abs_p5)
    assert admitted5
    assert reason5 is None


def test_binary_file_detection(tmp_path):
    binary_file = tmp_path / "sample.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")
    assert is_binary_file(binary_file)

    text_file = tmp_path / "sample.txt"
    text_file.write_text("Hello world")
    assert not is_binary_file(text_file)


def test_safe_extraction_and_flattening(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Wrapped in a single root folder
        zf.writestr("my-repo-master/README.md", "# Test Project")
        zf.writestr("my-repo-master/main.py", "print('hello')")
    buf.seek(0)

    target_dir = tmp_path / "extracted"
    extract_zip_safely(buf.getvalue(), target_dir)

    # Root wrapper should be stripped
    assert (target_dir / "README.md").exists()
    assert (target_dir / "main.py").exists()
    assert not (target_dir / "my-repo-master").exists()
