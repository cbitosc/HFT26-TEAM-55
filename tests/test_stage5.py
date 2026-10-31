"""Stage 5 Test Suite for CodeCompass.

Tests SQLite FTS5 Indexing, Search, Consistency, Atomicity, Rollback,
and Persistence after restart.
"""

import io
import os
import shutil
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

# Add backend directory to path if needed
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.database import get_db, init_db
from app.services.zip_validator import validate_and_extract_zip, ZipValidationError
from app.services.ast_parser import parse_python_file
from app.services.indexer import index_repository_contents, get_active_repository
from app.services.search_service import search_codebase, sanitize_fts5_query, SearchServiceError
from app.routers.repository import get_repository_status, upload_repository_archive
from app.routers.search import search_code
from fastapi import UploadFile
import asyncio


def create_test_zip(files_dict: dict, root_folder: str = "test-repo") -> bytes:
    """Helper to create an in-memory ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in files_dict.items():
            full_path = f"{root_folder}/{rel_path}" if root_folder else rel_path
            zf.writestr(full_path, content)
    return buf.getvalue()


class TestStage5IndexingAndSearch(unittest.TestCase):
    """Comprehensive test cases for Stage 5 SQLite FTS5 search and indexing."""

    def setUp(self):
        """Create an isolated temporary directory for testing SQLite database."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_codecompass.db"
        init_db(self.db_path)

    def tearDown(self):
        """Clean up temporary test files."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_database_initialization_and_fk_enabled(self):
        """Verify schema tables, virtual tables, and foreign keys are active."""
        with get_db(self.db_path) as con:
            cur = con.cursor()
            # Foreign keys check
            cur.execute("PRAGMA foreign_keys;")
            fk_status = cur.fetchone()[0]
            self.assertEqual(fk_status, 1, "Foreign keys must be enabled (PRAGMA foreign_keys = 1)")

            # Check tables exist
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = {row[0] for row in cur.fetchall()}
            self.assertIn("repositories", tables)
            self.assertIn("files", tables)
            self.assertIn("symbols", tables)
            self.assertIn("code_search_fts", tables)

    def test_indexing_valid_repository(self):
        """Verify indexing parses Python source, creates relational and FTS5 records."""
        sample_code_1 = '''"""Auth module."""

class UserManager:
    """Manages user accounts and credentials."""
    def __init__(self, db_conn):
        self.db_conn = db_conn

    def authenticate_user(self, username: str, token: str) -> bool:
        """Validate credentials for user session."""
        if not username:
            return False
        return token == "secret"
'''
        sample_code_2 = '''def calculate_metrics(values: list) -> float:
    """Compute mathematical average."""
    return sum(values) / len(values) if values else 0.0
'''
        zip_bytes = create_test_zip({
            "auth/user_mgr.py": sample_code_1,
            "analytics/calc.py": sample_code_2,
        }, root_folder="my-project-main")

        repo_name, python_files, skipped, warnings = validate_and_extract_zip(zip_bytes)
        self.assertEqual(repo_name, "my-project-main")
        self.assertEqual(len(python_files), 2)

        repo_id, total_files, total_symbols, total_lines, failed_files = index_repository_contents(
            repo_name=repo_name,
            python_files=python_files,
            db_path=self.db_path,
        )

        self.assertEqual(total_files, 2)
        self.assertEqual(len(failed_files), 0)
        self.assertGreater(total_symbols, 0)
        self.assertGreater(total_lines, 0)

        # Verify active repository
        active_repo = get_active_repository(self.db_path)
        self.assertIsNotNone(active_repo)
        self.assertEqual(active_repo["id"], repo_id)
        self.assertEqual(active_repo["name"], "my-project-main")
        self.assertEqual(active_repo["total_files"], 2)

        # Verify relational tables
        with get_db(self.db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM files WHERE repository_id = ?", (repo_id,))
            self.assertEqual(cur.fetchone()[0], 2)

            cur.execute("SELECT COUNT(*) FROM symbols WHERE repository_id = ?", (repo_id,))
            self.assertEqual(cur.fetchone()[0], total_symbols)

            cur.execute("SELECT COUNT(*) FROM code_search_fts WHERE repository_id = ?", (repo_id,))
            self.assertEqual(cur.fetchone()[0], total_symbols)

    def test_search_symbols_and_bm25_ranking(self):
        """Verify FTS5 search returns real symbol names, kinds, paths, line ranges, and highlights."""
        code = '''class DatabaseConnector:
    """Primary SQLite database connection manager."""
    def connect_to_database(self, url: str):
        """Establish active database connection session."""
        print("Connecting to", url)
'''
        zip_bytes = create_test_zip({"db/connector.py": code}, root_folder="db-lib")
        repo_name, python_files, _, _ = validate_and_extract_zip(zip_bytes)
        index_repository_contents(repo_name, python_files, db_path=self.db_path)

        # 1. Search for function/method
        res = search_codebase(query="connect_to_database", db_path=self.db_path)
        self.assertGreater(res["total_matches"], 0)
        self.assertEqual(res["repository_name"], "db-lib")

        top_match = res["results"][0]
        self.assertEqual(top_match["name"], "connect_to_database")
        self.assertEqual(top_match["kind"], "method")
        self.assertEqual(top_match["file_path"], "db/connector.py")
        self.assertEqual(top_match["parent_scope"], "DatabaseConnector")
        self.assertEqual(top_match["start_line"], 3)
        self.assertEqual(top_match["end_line"], 5)
        self.assertIn("Establish active database", top_match["docstring"])
        self.assertIn("def connect_to_database", top_match["snippet"])
        self.assertIn("<mark>", top_match["highlight"])
        self.assertIsInstance(top_match["rank"], float)

        # 2. Search for class
        class_res = search_codebase(query="DatabaseConnector", db_path=self.db_path)
        self.assertGreater(class_res["total_matches"], 0)
        self.assertEqual(class_res["results"][0]["name"], "DatabaseConnector")
        self.assertEqual(class_res["results"][0]["kind"], "class")

    def test_empty_and_whitespace_queries(self):
        """Verify empty and whitespace queries return empty results gracefully without errors."""
        code = 'def ping(): return "pong"\n'
        zip_bytes = create_test_zip({"ping.py": code})
        repo_name, python_files, _, _ = validate_and_extract_zip(zip_bytes)
        index_repository_contents(repo_name, python_files, db_path=self.db_path)

        for empty_q in ["", "   ", "\t\n", "???", "@#$%^"]:
            res = search_codebase(query=empty_q, db_path=self.db_path)
            self.assertEqual(res["total_matches"], 0)
            self.assertEqual(res["results"], [])

    def test_no_matches_query(self):
        """Verify queries with no matching symbols return total_matches == 0."""
        code = 'def compute_hash(data): return "hash"\n'
        zip_bytes = create_test_zip({"hasher.py": code})
        repo_name, python_files, _, _ = validate_and_extract_zip(zip_bytes)
        index_repository_contents(repo_name, python_files, db_path=self.db_path)

        res = search_codebase(query="nonexistent_alien_function_12345", db_path=self.db_path)
        self.assertEqual(res["total_matches"], 0)
        self.assertEqual(res["results"], [])
        self.assertEqual(res["repository_name"], "test-repo")

    def test_repository_replacement_atomicity(self):
        """Verify replacing a repository purges old relational & FTS records atomically."""
        # Index Repo 1
        zip1 = create_test_zip({"alpha.py": "def function_alpha(): pass\n"}, root_folder="repo-alpha")
        rname1, files1, _, _ = validate_and_extract_zip(zip1)
        repo_id1, _, _, _, _ = index_repository_contents(rname1, files1, db_path=self.db_path)

        res1 = search_codebase("function_alpha", db_path=self.db_path)
        self.assertEqual(res1["total_matches"], 1)

        # Index Repo 2 (Replacement)
        zip2 = create_test_zip({"beta.py": "def function_beta(): pass\n"}, root_folder="repo-beta")
        rname2, files2, _, _ = validate_and_extract_zip(zip2)
        repo_id2, _, _, _, _ = index_repository_contents(rname2, files2, db_path=self.db_path)

        self.assertNotEqual(repo_id1, repo_id2)

        # Active repo must be Repo 2
        active = get_active_repository(self.db_path)
        self.assertEqual(active["id"], repo_id2)
        self.assertEqual(active["name"], "repo-beta")

        # Repo 2 symbol must be found
        res_beta = search_codebase("function_beta", db_path=self.db_path)
        self.assertEqual(res_beta["total_matches"], 1)
        self.assertEqual(res_beta["results"][0]["name"], "function_beta")

        # Repo 1 symbol must NO LONGER be returned
        res_alpha = search_codebase("function_alpha", db_path=self.db_path)
        self.assertEqual(res_alpha["total_matches"], 0)

        # Verify old repo records are deleted from repositories, files, symbols, and FTS
        with get_db(self.db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM repositories WHERE id = ?", (repo_id1,))
            self.assertEqual(cur.fetchone()[0], 0, "Old repo record must be purged")

            cur.execute("SELECT COUNT(*) FROM files WHERE repository_id = ?", (repo_id1,))
            self.assertEqual(cur.fetchone()[0], 0, "Old files must be cascaded")

            cur.execute("SELECT COUNT(*) FROM symbols WHERE repository_id = ?", (repo_id1,))
            self.assertEqual(cur.fetchone()[0], 0, "Old symbols must be cascaded")

            cur.execute("SELECT COUNT(*) FROM code_search_fts WHERE repository_id = ?", (repo_id1,))
            self.assertEqual(cur.fetchone()[0], 0, "Old FTS records must be purged")

    def test_rollback_on_indexing_failure(self):
        """Verify transaction rollback preserves previous active repository on failure."""
        # Index initial working repository
        zip1 = create_test_zip({"work.py": "def working_feature(): pass\n"}, root_folder="repo-stable")
        rname1, files1, _, _ = validate_and_extract_zip(zip1)
        repo_id1, _, _, _, _ = index_repository_contents(rname1, files1, db_path=self.db_path)

        active_before = get_active_repository(self.db_path)
        self.assertEqual(active_before["id"], repo_id1)

        # Attempt indexing with an invalid payload where all files have syntax errors
        bad_files = {"broken.py": "def broken_syntax(::: invalid"}
        with self.assertRaises(ValueError):
            index_repository_contents("repo-broken", bad_files, db_path=self.db_path)

        # State must remain identical to repo 1
        active_after = get_active_repository(self.db_path)
        self.assertEqual(active_after["id"], repo_id1)
        self.assertEqual(active_after["name"], "repo-stable")

        search_res = search_codebase("working_feature", db_path=self.db_path)
        self.assertEqual(search_res["total_matches"], 1)

    def test_persistence_after_restart(self):
        """Verify SQLite database persists on disk across separate connection sessions."""
        zip_bytes = create_test_zip({"persist.py": "def persistent_kernel(): return True\n"})
        rname, files, _, _ = validate_and_extract_zip(zip_bytes)
        index_repository_contents(rname, files, db_path=self.db_path)

        # Simulate app restart: open brand new connection to the file on disk
        with get_db(self.db_path) as fresh_con:
            cur = fresh_con.cursor()
            cur.execute("SELECT name FROM repositories WHERE is_active = 1")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["name"], "test-repo")

        # Search via fresh connection
        res = search_codebase("persistent_kernel", db_path=self.db_path)
        self.assertEqual(res["total_matches"], 1)
        self.assertEqual(res["results"][0]["name"], "persistent_kernel")

    def test_intelligent_exclusion_of_build_artifacts_and_large_bundles(self):
        """Verify generated files >256 KiB in excluded dirs (like dist/index.js) are ignored without error."""
        # ~280 KiB simulated JS bundle with realistic identifier entropy to prevent zip bomb ratio false positives
        lines = [f"function bundleComponent_{i}() {{ return '{i:x}' + '{i * 13}'; }}\n" for i in range(5000)]
        large_bundle_content = "".join(lines)
        self.assertGreater(len(large_bundle_content.encode("utf-8")), 256 * 1024)

        files = {
            "app/main.py": "def run_server(): return 'online'\n",
            "dist/assets/index-C1X01ujd.js": large_bundle_content,
            "node_modules/express/index.js": "module.exports = {};\n",
            ".venv/lib/site-packages/vendor.py": "def vendor_helper(): pass\n",
            "coverage/lcov.info": "TN:\nSF:app/main.py\nend_of_record\n",
            ".pytest_cache/v/cache/nodeids": "[]\n",
        }
        zip_bytes = create_test_zip(files, root_folder="my-app")

        # Must succeed without throwing ZipValidationError
        repo_name, python_files, skipped, _ = validate_and_extract_zip(zip_bytes)
        self.assertEqual(repo_name, "my-app")
        # Only app/main.py should be indexed as eligible Python file
        self.assertIn("app/main.py", python_files)
        self.assertEqual(len(python_files), 1)

        # Excluded and non-python files should be recorded in skipped
        self.assertTrue(any("dist/assets/index-C1X01ujd.js" in p for p in skipped))
        self.assertTrue(any("node_modules" in p for p in skipped))
        self.assertTrue(any(".venv" in p for p in skipped))

    def test_oversized_python_source_file_rejected(self):
        """Verify an eligible Python source file >256 KiB is strictly rejected."""
        # Generate >256 KiB Python code
        lines = [f"def function_number_{i}():\n    return {i * 12345}\n" for i in range(6000)]
        large_python_content = "".join(lines)
        self.assertGreater(len(large_python_content.encode("utf-8")), 256 * 1024)

        zip_bytes = create_test_zip({
            "app/giant_script.py": large_python_content,
        })
        with self.assertRaises(ZipValidationError) as ctx:
            validate_and_extract_zip(zip_bytes)
        self.assertIn("exceeds maximum allowed size of 256 KiB", str(ctx.exception))


class TestRouterEndpoints(unittest.TestCase):
    """Test API router endpoints directly."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_api.db"
        init_db(self.db_path)

        # Patch database, indexer & search services to use this test db
        import app.db.database as db_module
        import app.services.indexer as idx_module
        import app.services.search_service as search_module
        self.orig_db_path = db_module.DB_PATH
        self.orig_idx_db = idx_module.DB_PATH
        self.orig_search_db = search_module.DB_PATH
        db_module.DB_PATH = self.db_path
        idx_module.DB_PATH = self.db_path
        search_module.DB_PATH = self.db_path

    def tearDown(self):
        import app.db.database as db_module
        import app.services.indexer as idx_module
        import app.services.search_service as search_module
        db_module.DB_PATH = self.orig_db_path
        idx_module.DB_PATH = self.orig_idx_db
        search_module.DB_PATH = self.orig_search_db
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_repository_status_empty(self):
        status_res = get_repository_status()
        self.assertFalse(status_res["has_repository"])
        self.assertIsNone(status_res["repository"])

    def test_upload_archive_and_search_endpoints(self):
        zip_bytes = create_test_zip({
            "service/auth.py": "def verify_credentials(user, pwd):\n    return True\n"
        }, root_folder="service-repo")

        upload_file = UploadFile(
            file=io.BytesIO(zip_bytes),
            filename="service-repo.zip",
        )

        upload_res = asyncio.run(upload_repository_archive(upload_file))
        self.assertEqual(upload_res["status"], "indexed")
        self.assertEqual(upload_res["repo_name"], "service-repo")
        self.assertEqual(upload_res["total_files"], 1)

        # Check status endpoint now has repository
        status_res = get_repository_status()
        self.assertTrue(status_res["has_repository"])
        self.assertEqual(status_res["repository"]["name"], "service-repo")

        # Search endpoint
        search_res = search_code(q="verify_credentials")
        self.assertEqual(search_res["total_matches"], 1)
        self.assertEqual(search_res["results"][0]["name"], "verify_credentials")
        self.assertEqual(search_res["results"][0]["kind"], "function")


if __name__ == "__main__":
    unittest.main()
