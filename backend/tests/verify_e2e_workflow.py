"""End-to-End Workflow Verification for Stage 5 CodeCompass.

Simulates the complete HTTP upload-to-search workflow against the FastAPI application
including lifespan database initialization, repository ingestion, FTS5 BM25 search,
and atomic repository replacement.
"""

import asyncio
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

# Add backend directory
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import UploadFile
from app.main import app, lifespan
from app.db.database import get_db, init_db, DB_PATH
import app.db.database as db_mod
import app.services.indexer as idx_mod
import app.services.search_service as search_mod
from app.routers.repository import get_repository_status, upload_repository_archive
from app.routers.search import search_code


def make_zip(files: dict, root: str = "project-root") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p, code in files.items():
            zf.writestr(f"{root}/{p}", code)
    return buf.getvalue()


class TestE2EWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "e2e_codecompass.db"
        self.orig_db = db_mod.DB_PATH
        self.orig_idx_db = idx_mod.DB_PATH
        self.orig_search_db = search_mod.DB_PATH
        db_mod.DB_PATH = self.db_path
        idx_mod.DB_PATH = self.db_path
        search_mod.DB_PATH = self.db_path

    def tearDown(self):
        db_mod.DB_PATH = self.orig_db
        idx_mod.DB_PATH = self.orig_idx_db
        search_mod.DB_PATH = self.orig_search_db
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_e2e_workflow(self):
        # 1. Startup Lifespan: DB Initialization
        async def run_lifespan():
            async with lifespan(app):
                # Verify DB tables created
                with get_db(self.db_path) as con:
                    cur = con.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = {r[0] for r in cur.fetchall()}
                    self.assertIn("repositories", tables)
                    self.assertIn("code_search_fts", tables)

                # 2. Step: Check status before upload (empty)
                status_initial = get_repository_status()
                self.assertFalse(status_initial["has_repository"])
                self.assertIsNone(status_initial["repository"])

                # 3. Step: Upload & Index Repository 1
                repo1_files = {
                    "auth/service.py": '''"""Authentication service."""

class AuthService:
    """Handles secure user authentication and token verification."""
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def verify_auth_token(self, token: str) -> bool:
        """Verify the user JWT token validity."""
        return len(token) > 10
''',
                    "router/routes.py": '''"""Routing endpoints."""

def handle_login_request(request):
    """Processes inbound login HTTP POST request."""
    return {"status": "authorized"}
'''
                }
                zip_data_1 = make_zip(repo1_files, root="codecompass-core")
                upload_file_1 = UploadFile(
                    file=io.BytesIO(zip_data_1),
                    filename="codecompass-core.zip"
                )

                upload_res = await upload_repository_archive(upload_file_1)
                self.assertEqual(upload_res["status"], "indexed")
                self.assertEqual(upload_res["repo_name"], "codecompass-core")
                self.assertEqual(upload_res["total_files"], 2)
                self.assertGreater(upload_res["total_symbols"], 0)

                # 4. Step: Check status after upload
                status_after = get_repository_status()
                self.assertTrue(status_after["has_repository"])
                repo_meta = status_after["repository"]
                self.assertEqual(repo_meta["name"], "codecompass-core")
                self.assertEqual(repo_meta["total_files"], 2)

                # 5. Step: Search queries
                # 5a. Search for method
                res_method = search_code(q="verify_auth_token")
                self.assertGreater(res_method["total_matches"], 0)
                match = res_method["results"][0]
                self.assertEqual(match["name"], "verify_auth_token")
                self.assertEqual(match["kind"], "method")
                self.assertEqual(match["file_path"], "auth/service.py")
                self.assertEqual(match["parent_scope"], "AuthService")
                self.assertIn("Verify the user JWT token", match["docstring"])
                self.assertIn("def verify_auth_token", match["snippet"])
                self.assertIn("<mark>", match["highlight"])

                # 5b. Search for class
                res_class = search_code(q="AuthService")
                self.assertGreater(res_class["total_matches"], 0)
                self.assertEqual(res_class["results"][0]["name"], "AuthService")
                self.assertEqual(res_class["results"][0]["kind"], "class")

                # 5c. Search for function
                res_fn = search_code(q="handle_login_request")
                self.assertGreater(res_fn["total_matches"], 0)
                self.assertEqual(res_fn["results"][0]["name"], "handle_login_request")
                self.assertEqual(res_fn["results"][0]["kind"], "function")

                # 5d. Search for concept in docstrings
                res_doc = search_code(q="processes inbound login")
                self.assertGreater(res_doc["total_matches"], 0)

                # 5e. Search non-existent token
                res_empty = search_code(q="nonexistent_alien_symbol")
                self.assertEqual(res_empty["total_matches"], 0)
                self.assertEqual(res_empty["results"], [])

                # 6. Step: Atomic replacement with Repository 2
                repo2_files = {
                    "payment/stripe.py": '''class StripeProcessor:
    """Stripe checkout processor."""
    def charge_customer(self, customer_id: str, amount: int):
        """Processes credit card payment."""
        return True
'''
                }
                zip_data_2 = make_zip(repo2_files, root="payment-engine")
                upload_file_2 = UploadFile(
                    file=io.BytesIO(zip_data_2),
                    filename="payment-engine.zip"
                )

                upload_res_2 = await upload_repository_archive(upload_file_2)
                self.assertEqual(upload_res_2["repo_name"], "payment-engine")

                # Verify new active repository
                status_final = get_repository_status()
                self.assertEqual(status_final["repository"]["name"], "payment-engine")

                # Search new repository
                res_new = search_code(q="charge_customer")
                self.assertGreaterEqual(res_new["total_matches"], 1)
                self.assertEqual(res_new["results"][0]["name"], "charge_customer")

                # Verify old repository symbols are purged from FTS and relational tables
                res_old = search_code(q="verify_auth_token")
                self.assertEqual(res_old["total_matches"], 0)

        asyncio.run(run_lifespan())


if __name__ == "__main__":
    unittest.main()
