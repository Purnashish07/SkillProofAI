import os
import sys
import unittest
import json
import datetime
import sqlite3
import atexit
import tempfile
from pathlib import Path
import asyncio
import httpx
from httpx import ASGITransport

# Set backend working directory and import app
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

# Use a unique temporary database so test runs cannot touch project data.
TEST_DB_TEMP = tempfile.TemporaryDirectory(prefix="skillproof-integration-")
TEST_DB_PATH = Path(TEST_DB_TEMP.name) / "skillproof.db"
atexit.register(TEST_DB_TEMP.cleanup)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from app.database import init_db, conn
from app.security import pwd, token
from app.main import app

class SkillProofComprehensiveTestSuite(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize test database
        init_db()
        # Prepopulate an existing legacy user (like representative test fixture)
        with conn() as c:
            c.execute(
                "INSERT INTO users(name, email, password_hash, college) VALUES(?,?,?,?)",
                ("Legacy User", "legacy@example.org", pwd.hash("ExistingPassword123#"), "Tech Institute"),
            )
            c.commit()
        # Create a shared AsyncClient for the ASGI app
        cls.client = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")

    @classmethod
    async def asyncTearDownClass(cls):
        await cls.client.aclose()
        TEST_DB_TEMP.cleanup()

    async def test_01_health_check(self):
        res = await self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "SkillProof AI")

    async def test_02_legacy_register_success(self):
        res = await self.client.post("/api/auth/register", json={
            "name": "New Student",
            "email": "student1@example.org",
            "password": "Password123#",
            "college": "State University"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["email"], "student1@example.org")
        self.assertEqual(data["user"]["college"], "State University")

    async def test_03_legacy_register_duplicate_email(self):
        res = await self.client.post("/api/auth/register", json={
            "name": "Duplicate Student",
            "email": "student1@example.org",
            "password": "Password123#",
            "college": "State University"
        })
        self.assertEqual(res.status_code, 409)

    async def test_04_legacy_login_success(self):
        res = await self.client.post("/api/auth/login", json={
            "email": "legacy@example.org",
            "password": "ExistingPassword123#"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["name"], "Legacy User")

    async def test_05_legacy_login_invalid_password(self):
        res = await self.client.post("/api/auth/login", json={
            "email": "legacy@example.org",
            "password": "WrongPassword999!"
        })
        self.assertEqual(res.status_code, 401)

    async def test_06_protected_me_endpoint_with_valid_token(self):
        login_res = await self.client.post("/api/auth/login", json={
            "email": "legacy@example.org",
            "password": "ExistingPassword123#"
        })
        t = login_res.json()["access_token"]
        res = await self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {t}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["email"], "legacy@example.org")

    async def test_07_protected_me_endpoint_unauthorized(self):
        res = await self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 401)

    async def test_08_protected_me_endpoint_invalid_token(self):
        res = await self.client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        self.assertEqual(res.status_code, 401)

    async def test_09_supabase_sync_mocked_verified_new_user(self):
        from app.security import get_or_sync_supabase_user
        mock_identity = {
            "supabase_user_id": "sb-uuid-12345",
            "email": "new_supabase_user@example.org",
            "name": "Supabase Student",
            "college": "Engineering College"
        }
        res = get_or_sync_supabase_user(mock_identity)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["user"]["email"], "new_supabase_user@example.org")
        self.assertEqual(res["user"]["name"], "Supabase Student")
        self.assertEqual(res["user"]["college"], "Engineering College")
        self.assertIn("access_token", res)
        # Verify password_hash is NULL in SQLite for pure Supabase user
        with conn() as c:
            row = c.execute("SELECT password_hash, supabase_user_id FROM users WHERE id = ?",
                            (res["user"]["id"],)).fetchone()
            self.assertIsNone(row["password_hash"])
            self.assertEqual(row["supabase_user_id"], "sb-uuid-12345")

    async def test_10_supabase_sync_existing_local_user_requires_linking(self):
        from app.security import get_or_sync_supabase_user
        mock_identity = {
            "supabase_user_id": "sb-uuid-legacy-attacker-or-owner",
            "email": "legacy@example.org",
            "name": "Legacy User",
            "college": "Tech Institute"
        }
        res = get_or_sync_supabase_user(mock_identity)
        self.assertEqual(res["status"], "requires_linking")
        self.assertTrue(res["has_password"])

    async def test_11_supabase_link_wrong_password_rejected(self):
        from app.security import link_existing_account_with_supabase
        from fastapi import HTTPException
        mock_identity = {
            "supabase_user_id": "sb-uuid-legacy-real-owner",
            "email": "legacy@example.org",
        }
        with self.assertRaises(HTTPException) as ctx:
            link_existing_account_with_supabase(mock_identity, "WrongPassword!")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_12_supabase_link_correct_password_links_and_preserves_id(self):
        from app.security import link_existing_account_with_supabase
        mock_identity = {
            "supabase_user_id": "sb-uuid-legacy-real-owner",
            "email": "legacy@example.org",
        }
        res = link_existing_account_with_supabase(mock_identity, "ExistingPassword123#")
        self.assertEqual(res["status"], "linked")
        self.assertEqual(res["user"]["email"], "legacy@example.org")
        # Verify original user ID is 1 (the first user created)
        with conn() as c:
            row = c.execute("SELECT id, supabase_user_id FROM users WHERE email = 'legacy@example.org'").fetchone()
            self.assertEqual(row["id"], 1)
            self.assertEqual(row["supabase_user_id"], "sb-uuid-legacy-real-owner")

    async def test_13_supabase_duplicate_linking_rejected(self):
        from app.security import link_existing_account_with_supabase
        from fastapi import HTTPException
        mock_identity = {
            "supabase_user_id": "sb-uuid-legacy-real-owner",
            "email": "legacy@example.org",
        }
        with self.assertRaises(HTTPException) as ctx:
            link_existing_account_with_supabase(mock_identity, "ExistingPassword123#")
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_14_resume_analysis_and_history(self):
        # Login legacy user
        login_res = await self.client.post("/api/auth/login", json={
            "email": "legacy@example.org",
            "password": "ExistingPassword123#"
        })
        t = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {t}"}
        # Create dummy valid PDF in memory
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "John Doe\nSummary: Software Engineer experienced with Python, React, and SQL database optimization.\nBuilt a Python microservice with REST APIs and deployed on Docker.")
        pdf_bytes = doc.write()
        doc.close()
        files = {"resume": ("resume.pdf", pdf_bytes, "application/pdf")}
        data = {
            "job_description": "We are seeking a Software Development Engineer with Python, React, REST APIs, SQL, and Docker experience. Must have 2+ years building services.",
            "role_title": "Software Engineer"
        }
        res = await self.client.post("/api/analyze", headers=headers, files=files, data=data)
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertIsNotNone(result.get("analysis_id"))
        self.assertEqual(result["role_title"], "Software Engineer")
        self.assertIn("readiness", result["summary"])
        self.assertGreater(result["summary"]["readiness"], 0)
        self.assertTrue(len(result["skills"]) > 0)
        self.assertTrue(len(result["action_plan"]) > 0)
        analysis_id = result["analysis_id"]
        # Check history
        h_res = await self.client.get("/api/analyses", headers=headers)
        self.assertEqual(h_res.status_code, 200)
        items = h_res.json()
        self.assertTrue(len(items) >= 1)
        self.assertEqual(items[0]["id"], analysis_id)
        # Check single analysis retrieve
        single_res = await self.client.get(f"/api/analyses/{analysis_id}", headers=headers)
        self.assertEqual(single_res.status_code, 200)
        self.assertEqual(single_res.json()["role_title"], "Software Engineer")
        # Check PDF report generation
        pdf_res = await self.client.get(f"/api/analyses/{analysis_id}/report", headers=headers)
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers["content-type"], "application/pdf")
        self.assertTrue(len(pdf_res.content) > 1000)
        # Test data isolation: Another user cannot access analysis_id
        other_user_res = await self.client.post("/api/auth/register", json={
            "name": "Other Student",
            "email": "other@example.org",
            "password": "Password123#",
            "college": "Different College"
        })
        other_token = other_user_res.json()["access_token"]
        isolated_res = await self.client.get(f"/api/analyses/{analysis_id}", headers={"Authorization": f"Bearer {other_token}"})
        self.assertEqual(isolated_res.status_code, 404)
        # Check college overview
        college_res = await self.client.get("/api/college/overview", headers=headers)
        self.assertEqual(college_res.status_code, 200)
        cdata = college_res.json()
        self.assertEqual(cdata["college"], "Tech Institute")
        self.assertEqual(cdata["analyses"], 1)

    async def test_14b_export_pdf_for_history_loaded_analysis(self):
        """Regression test for the PDF export bug."""
        # Login legacy user
        login_res = await self.client.post("/api/auth/login", json={
            "email": "legacy@example.org",
            "password": "ExistingPassword123#"
        })
        token_val = login_res.json()["access_token"]
        self.assertTrue(token_val)
        headers = {"Authorization": f"Bearer {token_val}"}
        # Run a fresh analysis
        import fitz, io as _io
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Alice Nguyen\nBuilt Python REST APIs with FastAPI, React UI, SQL queries, Git workflows.")
        pdf_bytes = doc.write()
        doc.close()
        analyze_res = await self.client.post(
            "/api/analyze",
            headers=headers,
            files={"resume": ("alice.pdf", _io.BytesIO(pdf_bytes), "application/pdf")},
            data={
                "job_description": "We need Python, React, REST APIs, SQL, Git, Docker and Agile practices. Build reliable software, write tests, collaborate in an Agile team, and communicate technical decisions clearly.",
                "role_title": "Export Regression Role"
            }
        )
        self.assertEqual(analyze_res.status_code, 200)
        analyze_data = analyze_res.json()
        self.assertIsNotNone(analyze_data.get("analysis_id"))
        aid = analyze_data["analysis_id"]
        # GET analysis
        open_res = await self.client.get(f"/api/analyses/{aid}", headers=headers)
        self.assertEqual(open_res.status_code, 200)
        detail = open_res.json()
        self.assertIsNotNone(detail.get("analysis_id"))
        self.assertEqual(detail["analysis_id"], aid)
        self.assertTrue(bool(detail["analysis_id"]))
        # PDF export
        pdf_res = await self.client.get(f"/api/analyses/{aid}/report", headers=headers)
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers["content-type"], "application/pdf")
        self.assertTrue(len(pdf_res.content) > 500)
        # Guest cannot export
        guest_res = await self.client.get(f"/api/analyses/{aid}/report")
        self.assertIn(guest_res.status_code, [401, 403])

    async def test_15_invalid_pdf_validation(self):
        login_res = await self.client.post("/api/auth/login", json={
            "email": "legacy@example.org",
            "password": "ExistingPassword123#"
        })
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
        # Non-pdf file extension
        files = {"resume": ("resume.txt", b"plain text", "text/plain")}
        data = {"job_description": "A" * 100, "role_title": "Engineer"}
        res = await self.client.post("/api/analyze", headers=headers, files=files, data=data)
        self.assertEqual(res.status_code, 415)
        # Short job description (< 80 chars)
        files = {"resume": ("resume.pdf", b"%PDF-1.4 dummy", "application/pdf")}
        data = {"job_description": "Too short", "role_title": "Engineer"}
        res = await self.client.post("/api/analyze", headers=headers, files=files, data=data)
        self.assertEqual(res.status_code, 422)

    async def test_16_jwt_expiration(self):
        # Temporarily set short expiry via env
        orig = os.getenv("JWT_EXP_SECONDS")
        os.environ["JWT_EXP_SECONDS"] = "1"
        from importlib import reload
        import app.security as sec_mod
        reload(sec_mod)
        short_token = sec_mod.token(9999)  # generate token with 1 sec ttl
        # Wait for 2 seconds
        await asyncio.sleep(2)
        # Access protected endpoint with expired token
        res = await self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {short_token}"})
        self.assertEqual(res.status_code, 401)
        # Restore env
        if orig is None:
            del os.environ["JWT_EXP_SECONDS"]
        else:
            os.environ["JWT_EXP_SECONDS"] = orig
        reload(sec_mod)

    async def test_17_cors_headers(self):
        # Simple GET should include Access-Control-Allow-Origin for allowed origin
        res = await self.client.options("/api/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
        self.assertEqual(res.status_code, 200)
        self.assertIn(res.headers.get("access-control-allow-origin"), ["http://localhost:5173", "*"])

    async def test_18_guest_explorer_isolation(self):
        # Guest (no token) trying to access protected route
        res = await self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 401)
