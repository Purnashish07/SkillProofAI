import io
import json
from typing import Optional
import fitz
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import os

from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from .database import init_db, conn
from .config import validate_production_secret_key
from .security import (
    pwd,
    token,
    current,
    required,
    verify_supabase_access_token,
    get_or_sync_supabase_user,
    link_existing_account_with_supabase,
)
from .engine import analyse

app = FastAPI(title="SkillProof AI API", version="1.0.0")

from urllib.parse import urlparse

# Determine environment and configure CORS origins securely
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if ENVIRONMENT == "production":
    validate_production_secret_key()

def _parse_and_validate_origins(origins_str: str) -> list[str]:
    raw_list = [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    validated = []
    for origin in raw_list:
        if origin == "*":
            raise RuntimeError("Wildcard origin '*' cannot be used with credentials enabled in ALLOWED_ORIGINS")
        p = urlparse(origin)
        if p.scheme not in ("http", "https") or not p.netloc or p.path not in ("", "/") or p.query or p.params or p.fragment:
            raise RuntimeError(f"Malformed origin in ALLOWED_ORIGINS: {origin}")
        validated.append(f"{p.scheme}://{p.netloc}")
    return validated

if ENVIRONMENT == "production":
    raw_origins = os.getenv("ALLOWED_ORIGINS")
    if raw_origins is None:
        raise RuntimeError("ALLOWED_ORIGINS must be set in production environment")
    if not raw_origins.strip():
        raise RuntimeError("ALLOWED_ORIGINS cannot be empty in production environment")
    allowed_origins = _parse_and_validate_origins(raw_origins)
    if not allowed_origins:
        raise RuntimeError("ALLOWED_ORIGINS cannot be empty in production environment")
else:
    default_dev = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    raw_origins = os.getenv("ALLOWED_ORIGINS", default_dev)
    allowed_origins = _parse_and_validate_origins(raw_origins) if raw_origins.strip() else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    college: str = ""


class Login(BaseModel):
    email: EmailStr
    password: str


class SupabaseSyncRequest(BaseModel):
    college: Optional[str] = None
    name: Optional[str] = None


class LinkAccountRequest(BaseModel):
    password: str = Field(min_length=1, description="Existing local SkillProof password")


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=80)
    college: Optional[str] = Field(None, max_length=120)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SkillProof AI"}


# Legacy auth endpoints
@app.post("/api/auth/register")
def register(b: Register):
    norm_email = b.email.strip().lower()
    with conn() as c:
        try:
            cur = c.execute(
                "INSERT INTO users(name, email, password_hash, college) VALUES(?,?,?,?)",
                (b.name.strip(), norm_email, pwd.hash(b.password), b.college.strip()),
            )
            c.commit()
        except Exception:
            raise HTTPException(409, "An account with this email may already exist")
    u = {
        "id": cur.lastrowid,
        "name": b.name.strip(),
        "email": norm_email,
        "college": b.college.strip(),
    }
    return {"access_token": token(u["id"]), "user": u}


@app.post("/api/auth/login")
def login(b: Login):
    norm_email = b.email.strip().lower()
    with conn() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (norm_email,)).fetchone()
    if not r or not r["password_hash"] or not pwd.verify(b.password, r["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    u = {
        "id": r["id"],
        "name": r["name"],
        "email": r["email"],
        "college": r["college"],
    }
    return {"access_token": token(u["id"]), "user": u}


# Supabase auth sync & link endpoints
@app.post("/api/auth/supabase/sync")
def supabase_sync(
    body: Optional[SupabaseSyncRequest] = None,
    authorization: Optional[str] = Header(None),
):
    """
    Called after Supabase client login/signup.
    Verifies the Supabase access token via backend Supabase Auth.
    If the identity is already linked to SQLite user, returns the user.
    If email belongs to an existing SQLite user without this Supabase ID, returns status: requires_linking.
    If new, provisions a new SQLite record.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    access_token = authorization.split(" ", 1)[1].strip()
    identity = verify_supabase_access_token(access_token)

    name_override = body.name if body and body.name else None
    college_override = body.college if body and body.college else None

    result = get_or_sync_supabase_user(
        identity,
        name_override=name_override,
        college_override=college_override,
    )
    return result


@app.post("/api/auth/supabase/link")
def supabase_link(
    body: LinkAccountRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Securely link an existing SQLite user to the verified Supabase identity.
    Requires the user's legacy password to verify ownership.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    access_token = authorization.split(" ", 1)[1].strip()
    identity = verify_supabase_access_token(access_token)

    result = link_existing_account_with_supabase(identity, body.password)
    return result


@app.get("/api/auth/me")
def me(u=Depends(required)):
    return u


@app.put("/api/auth/profile")
def update_profile(body: UpdateProfileRequest, u=Depends(required)):
    user_id = u["id"]
    new_name = body.name.strip() if body.name is not None else u["name"]
    new_college = body.college.strip() if body.college is not None else (u.get("college") or "")

    if not new_name:
        raise HTTPException(422, "Name cannot be empty")

    with conn() as c:
        c.execute(
            "UPDATE users SET name = ?, college = ? WHERE id = ?",
            (new_name, new_college, user_id),
        )
        c.commit()
        row = c.execute(
            "SELECT id, name, email, college FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        raise HTTPException(404, "User not found")

    return dict(row)


@app.post("/api/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    role_title: str = Form("Target role"),
    u=Depends(current),
):
    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Upload a PDF resume")
    if len(job_description.strip()) < 80:
        raise HTTPException(
            422,
            "Please provide a detailed job description (at least 80 characters)",
        )
    data = await resume.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Resume must be 8 MB or smaller")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n".join(p.get_text() for p in doc)
        doc.close()
    except Exception:
        raise HTTPException(422, "Could not read this PDF")
    if not text.strip():
        raise HTTPException(
            422,
            "No selectable text found. Scanned PDFs need OCR before analysis",
        )
    result = analyse(text, job_description, role_title)
    result["resume_name"] = resume.filename
    result["analysis_id"] = None
    if u:
        with conn() as c:
            cur = c.execute(
                "INSERT INTO analyses(user_id,role_title,resume_name,result_json) VALUES(?,?,?,?)",
                (u["id"], role_title, resume.filename, json.dumps(result)),
            )
            c.commit()
            result["analysis_id"] = cur.lastrowid
            # Update stored JSON so it also contains the correct analysis_id.
            c.execute(
                "UPDATE analyses SET result_json=? WHERE id=?",
                (json.dumps(result), cur.lastrowid),
            )
            c.commit()
    return result


@app.get("/api/analyses")
def history(u=Depends(required)):
    with conn() as c:
        rows = c.execute(
            "SELECT id,role_title,resume_name,created_at,result_json FROM analyses WHERE user_id=? ORDER BY id DESC LIMIT 30",
            (u["id"],),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "role_title": r["role_title"],
            "resume_name": r["resume_name"],
            "created_at": r["created_at"],
            "summary": json.loads(r["result_json"])["summary"],
        }
        for r in rows
    ]


@app.get("/api/analyses/{aid}")
def get_analysis(aid: int, u=Depends(required)):
    with conn() as c:
        r = c.execute(
            "SELECT result_json FROM analyses WHERE id=? AND user_id=?",
            (aid, u["id"]),
        ).fetchone()
    if not r:
        raise HTTPException(404, "Analysis not found")
    data = json.loads(r["result_json"])
    # Always inject the real DB id so the frontend can use it for export,
    # even when the stored JSON was written before the id was available.
    data["analysis_id"] = aid
    return data


@app.get("/api/analyses/{aid}/report")
def pdf_report(aid: int, u=Depends(required)):
    with conn() as c:
        r = c.execute(
            "SELECT result_json FROM analyses WHERE id=? AND user_id=?",
            (aid, u["id"]),
        ).fetchone()
    if not r:
        raise HTTPException(404, "Analysis not found")
    d = json.loads(r["result_json"])
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    story = [
        Paragraph("SkillProof AI", styles["Title"]),
        Paragraph("Evidence-based career readiness report", styles["Heading2"]),
        Paragraph("Role: " + d["role_title"], styles["BodyText"]),
        Spacer(1, 12),
    ]
    s = d["summary"]
    story.append(
        Paragraph(
            f"Evidence coverage indicator: {s['readiness']}% (not a hiring score). Demonstrated: {s['demonstrated']} · Partial: {s['partial']} · Not evidenced: {s['missing']}",
            styles["BodyText"],
        )
    )
    story.append(Paragraph("Skill evidence map", styles["Heading2"]))
    for x in d["skills"]:
        story.append(
            Paragraph(
                f"<b>{x['skill']} — {x['status']}</b> · confidence {x['confidence']:.0%}",
                styles["BodyText"],
            )
        )
        story.append(Paragraph(x["interpretation"], styles["BodyText"]))
        for ev in x["evidence"]:
            story.append(
                Paragraph(
                    "Evidence: "
                    + ev["snippet"]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"),
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 6))
    story.append(Paragraph("Two-day proof projects", styles["Heading2"]))
    for p in d["action_plan"]:
        story.append(
            Paragraph(
                f"<b>{p['title']}</b> — {p['skill']}: {p['description']}",
                styles["BodyText"],
            )
        )
    story.append(Paragraph("Interview prompts", styles["Heading2"]))
    for q in d["interview_questions"]:
        story.append(
            Paragraph(q["skill"] + ": " + q["question"], styles["BodyText"])
        )
    story.append(Paragraph(d["disclaimer"], styles["Italic"]))
    SimpleDocTemplate(buf, pagesize=A4).build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="SkillProof_Action_Plan_{aid}.pdf"'
        },
    )


@app.get("/api/college/overview")
def college(u=Depends(required)):
    user_college = (u.get("college") or "").strip()
    if not user_college:
        return {
            "college": "",
            "analyses": 0,
            "evidence_totals": {"demonstrated": 0, "partial": 0, "missing": 0},
            "top_skill_gaps": [],
            "note": "Please update your college in your profile to view aggregate analytics.",
        }

    with conn() as c:
        rows = c.execute(
            "SELECT a.result_json FROM analyses a JOIN users u ON u.id=a.user_id WHERE u.college=?",
            (user_college,),
        ).fetchall()
    counts = {"demonstrated": 0, "partial": 0, "missing": 0}
    gaps = {}
    for row in rows:
        d = json.loads(row["result_json"])
        for k in counts:
            counts[k] += d["summary"].get(k, 0)
        for x in d.get("skills", []):
            z = gaps.setdefault(
                x["skill"],
                {"skill": x["skill"], "demonstrated": 0, "partial": 0, "missing": 0},
            )
            if x.get("status") in z:
                z[x["status"]] += 1
    return {
        "college": user_college,
        "analyses": len(rows),
        "evidence_totals": counts,
        "top_skill_gaps": sorted(
            gaps.values(), key=lambda x: x["missing"], reverse=True
        )[:8],
        "note": "Aggregate prototype analytics; not a placement prediction.",
    }
