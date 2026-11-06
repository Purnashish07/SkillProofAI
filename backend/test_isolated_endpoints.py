import os
import sys
import unittest
import json
import datetime
import sqlite3
import atexit
import tempfile
from pathlib import Path
from starlette.datastructures import UploadFile
import io

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

# Use a unique temporary database so test runs cannot touch project data.
TEST_DB_TEMP = tempfile.TemporaryDirectory(prefix="skillproof-endpoints-")
TEST_DB_PATH = Path(TEST_DB_TEMP.name) / "skillproof.db"
atexit.register(TEST_DB_TEMP.cleanup)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from app.database import init_db, conn
from app.security import pwd, token, get_or_sync_supabase_user, link_existing_account_with_supabase
from app.main import (
    app,
    health,
    register,
    login,
    me,
    update_profile,
    Register,
    Login,
    LinkAccountRequest,
    UpdateProfileRequest,
    SupabaseSyncRequest,
    supabase_sync,
    supabase_link,
    history,
    get_analysis,
    pdf_report,
    college,
)
from fastapi import HTTPException
import fitz

class SkillProofEndpointDirectTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        with conn() as c:
            c.execute(
                "INSERT INTO users(name, email, password_hash, college) VALUES(?,?,?,?)",
                ("Legacy User", "legacy@example.org", pwd.hash("ExistingPassword123#"), "Tech Institute")
            )
            c.commit()

    @classmethod
    def tearDownClass(cls):
        TEST_DB_TEMP.cleanup()

    def test_01_health_check(self):
        res = health()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["service"], "SkillProof AI")

    def test_02_legacy_register_and_duplicate_check(self):
        reg = Register(name="Alice Bob", email="alice@example.org", password="Password123#", college="MIT")
        res = register(reg)
        self.assertIn("access_token", res)
        self.assertEqual(res["user"]["email"], "alice@example.org")

        # Duplicate register raises 409
        with self.assertRaises(HTTPException) as ctx:
            register(reg)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_03_legacy_login_and_invalid_passwords(self):
        log_obj = Login(email="legacy@example.org", password="ExistingPassword123#")
        res = login(log_obj)
        self.assertIn("access_token", res)
        self.assertEqual(res["user"]["name"], "Legacy User")

        with self.assertRaises(HTTPException) as ctx:
            login(Login(email="legacy@example.org", password="WrongPassword!"))
        self.assertEqual(ctx.exception.status_code, 401)

        with self.assertRaises(HTTPException) as ctx:
            login(Login(email="nonexistent@example.org", password="SomePassword!"))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_04_supabase_sync_provision_new_user(self):
        identity = {
            "supabase_user_id": "sb-fresh-user-uuid-1",
            "email": "fresh_sb@example.org",
            "name": "Fresh Student",
            "college": "Oxford",
        }
        res = get_or_sync_supabase_user(identity)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["user"]["email"], "fresh_sb@example.org")
        self.assertEqual(res["user"]["college"], "Oxford")
        self.assertIn("access_token", res)

        # Confirm password_hash is NULL in database
        with conn() as c:
            row = c.execute("SELECT password_hash, supabase_user_id FROM users WHERE email = ?", ("fresh_sb@example.org",)).fetchone()
            self.assertIsNone(row["password_hash"])
            self.assertEqual(row["supabase_user_id"], "sb-fresh-user-uuid-1")

    def test_05_supabase_sync_existing_local_user_requires_linking(self):
        identity = {
            "supabase_user_id": "sb-attacker-or-migrator-uuid",
            "email": "legacy@example.org",
            "name": "Legacy Person",
            "college": "Tech Institute",
        }
        res = get_or_sync_supabase_user(identity)
        self.assertEqual(res["status"], "requires_linking")
        self.assertTrue(res["has_password"])

    def test_06_supabase_link_account_flow(self):
        identity = {
            "supabase_user_id": "sb-real-owner-uuid",
            "email": "legacy@example.org",
        }

        # Incorrect password
        with self.assertRaises(HTTPException) as ctx:
            link_existing_account_with_supabase(identity, "BadPassword!")
        self.assertEqual(ctx.exception.status_code, 401)

        # Correct password
        res = link_existing_account_with_supabase(identity, "ExistingPassword123#")
        self.assertEqual(res["status"], "linked")
        self.assertEqual(res["user"]["email"], "legacy@example.org")

        with conn() as c:
            row = c.execute("SELECT id, supabase_user_id FROM users WHERE email = 'legacy@example.org'").fetchone()
            self.assertEqual(row["id"], 1) # preserved local id
            self.assertEqual(row["supabase_user_id"], "sb-real-owner-uuid")

        # Duplicate link attempt rejected
        with self.assertRaises(HTTPException) as ctx:
            link_existing_account_with_supabase(identity, "ExistingPassword123#")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_07_resume_analysis_and_endpoints(self):
        import asyncio
        from app.main import analyze

        # Create dummy PDF in memory
        doc = fitz.open()
        p = doc.new_page()
        p.insert_text((50, 50), "Senior Python Engineer\nBuilt and deployed high performance REST APIs using FastAPI and Docker.\nAutomated SQL databases with PostgreSQL and Git pipelines.")
        pdf_bytes = doc.write()
        doc.close()

        u = {"id": 1, "name": "Legacy User", "email": "legacy@example.org", "college": "Tech Institute"}

        upload_file = UploadFile(filename="resume.pdf", file=io.BytesIO(pdf_bytes))
        jd = "We are hiring a Python Software Engineer to build REST APIs, work with SQL databases, and deploy with Docker and Git. We also require Machine Learning, Cybersecurity, and AWS skills."

        res = asyncio.run(analyze(resume=upload_file, job_description=jd, role_title="Python Engineer", u=u))
        self.assertIsNotNone(res["analysis_id"])
        self.assertEqual(res["role_title"], "Python Engineer")
        self.assertGreater(res["summary"]["readiness"], 0)
        self.assertTrue(len(res["skills"]) > 0)
        self.assertTrue(len(res["action_plan"]) > 0)
        self.assertTrue(len(res["interview_questions"]) > 0)

        aid = res["analysis_id"]

        # History
        hist = history(u=u)
        self.assertTrue(len(hist) >= 1)
        self.assertEqual(hist[0]["id"], aid)

        # Single analysis
        single = get_analysis(aid=aid, u=u)
        self.assertEqual(single["role_title"], "Python Engineer")

        # Isolation: another user cannot access aid
        other_user = {"id": 2, "name": "Alice Bob", "email": "alice@example.org", "college": "MIT"}
        with self.assertRaises(HTTPException) as ctx:
            get_analysis(aid=aid, u=other_user)
        self.assertEqual(ctx.exception.status_code, 404)

        # ReportLab PDF report generation
        pdf_stream = pdf_report(aid=aid, u=u)
        self.assertEqual(pdf_stream.media_type, "application/pdf")
        self.assertIn("Content-Disposition", pdf_stream.headers)
        self.assertIn("attachment", pdf_stream.headers["Content-Disposition"])

        # College overview
        c_overview = college(u=u)
        self.assertEqual(c_overview["college"], "Tech Institute")
        self.assertEqual(c_overview["analyses"], 1)
        self.assertGreater(c_overview["evidence_totals"]["demonstrated"], 0)

    def test_08_get_analysis_injects_analysis_id_for_export(self):
        """
        Regression test for the PDF export bug.

        GET /api/analyses/{aid} must always return a non-null analysis_id
        so that the frontend exportPdf() function can pass it to the PDF
        report endpoint.  This is critical when the stored result_json was
        written before the DB row id was available (analysis_id was None at
        INSERT time in older code paths).
        """
        import asyncio
        import fitz
        import io as _io

        # Simulate the old bug: create an analysis row whose stored JSON
        # has analysis_id=null (as happened before the analyse() fix).
        u = {"id": 1, "name": "Legacy User", "email": "legacy@example.org", "college": "Tech Institute"}

        # Build a minimal result_json with analysis_id=None  (old format)
        broken_json = {
            "role_title": "Export Regression Role",
            "resume_name": "regression.pdf",
            "analysis_id": None,   # <-- the historic bug value
            "summary": {"total": 1, "demonstrated": 1, "partial": 0, "missing": 0, "readiness": 100},
            "skills": [],
            "action_plan": [],
            "interview_questions": [],
            "disclaimer": "test",
        }
        import json as _json
        with conn() as c:
            cur = c.execute(
                "INSERT INTO analyses(user_id,role_title,resume_name,result_json) VALUES(?,?,?,?)",
                (u["id"], "Export Regression Role", "regression.pdf", _json.dumps(broken_json)),
            )
            c.commit()
            regression_aid = cur.lastrowid

        # Verify the stored JSON really has analysis_id=None
        with conn() as c:
            row = c.execute("SELECT result_json FROM analyses WHERE id=?", (regression_aid,)).fetchone()
        stored = _json.loads(row["result_json"])
        self.assertIsNone(stored.get("analysis_id"), "Pre-condition: stored analysis_id should be None")

        # Now call get_analysis — it must return analysis_id == regression_aid
        result = get_analysis(aid=regression_aid, u=u)
        self.assertIsNotNone(result["analysis_id"], "analysis_id must NOT be None after get_analysis()")
        self.assertEqual(result["analysis_id"], regression_aid,
                         f"analysis_id must equal the DB row id {regression_aid}")

        # Confirm exportPdf() condition `result.analysis_id && token` would pass
        self.assertTrue(bool(result["analysis_id"]),
                        "analysis_id must be truthy so frontend exportPdf() check passes")

    def test_09_profile_update_successful_and_validation(self):
        """
        Verify PUT /api/auth/profile updates the user's name and college,
        validates input, and protects against unauthorized or empty values.
        """
        u = {"id": 1, "name": "Legacy User", "email": "legacy@example.org", "college": "Tech Institute"}

        # Successful update of both name and college
        req = UpdateProfileRequest(name="Updated Student", college="Stanford University")
        updated = update_profile(body=req, u=u)
        self.assertEqual(updated["name"], "Updated Student")
        self.assertEqual(updated["college"], "Stanford University")
        self.assertEqual(updated["email"], "legacy@example.org")

        # Persistence check in DB
        with conn() as c:
            row = c.execute("SELECT name, college, email FROM users WHERE id = 1").fetchone()
            self.assertEqual(row["name"], "Updated Student")
            self.assertEqual(row["college"], "Stanford University")

        # Empty name rejection
        with self.assertRaises(HTTPException) as ctx:
            update_profile(body=UpdateProfileRequest(name="   "), u=u)
        self.assertEqual(ctx.exception.status_code, 422)

        # Cross user protection / update only modifies row for u["id"]
        other_user = {"id": 999, "name": "Fake", "email": "fake@example.org", "college": ""}
        with self.assertRaises(HTTPException) as ctx:
            update_profile(body=UpdateProfileRequest(name="Hacker"), u=other_user)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_10_oversized_resume_is_rejected_after_bounded_read(self):
        import asyncio
        from app.main import analyze

        upload_file = UploadFile(
            filename="oversized.pdf",
            file=io.BytesIO(b"x" * (8 * 1024 * 1024 + 1)),
        )
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                analyze(
                    resume=upload_file,
                    job_description="A detailed job description with enough text " * 4,
                    role_title="Software Engineer",
                    u=None,
                )
            )
        self.assertEqual(ctx.exception.status_code, 413)

if __name__ == "__main__":
    unittest.main()
