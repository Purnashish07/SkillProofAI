import os
from datetime import datetime, timezone, timedelta


from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from supabase import create_client

from .config import SECRET_KEY, SUPABASE_URL, SUPABASE_KEY
from .database import conn


pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

_supabase = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)


def token(uid):
    # Token expiration can be configured via JWT_EXP_SECONDS env variable (default 86400 seconds = 1 day)
    exp_seconds = int(os.getenv("JWT_EXP_SECONDS", "86400"))
    return jwt.encode(
        {
            "sub": str(uid),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_seconds),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
    return jwt.encode(
        {
            "sub": str(uid),
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
        },
        SECRET_KEY,
        algorithm="HS256",
    )


def verify_supabase_access_token(access_token: str):
    if not _supabase:
        raise HTTPException(503, "Supabase authentication is not configured")

    try:
        response = _supabase.auth.get_user(access_token)
        user = getattr(response, "user", None)
    except Exception:
        raise HTTPException(401, "Invalid or expired Supabase session")

    if not user:
        raise HTTPException(401, "Invalid Supabase session")

    email = getattr(user, "email", None)
    email_verified = (
        getattr(user, "email_confirmed_at", None)
        or getattr(user, "confirmed_at", None)
    )

    if not email or not email_verified:
        raise HTTPException(403, "Please verify your email before continuing")

    metadata = getattr(user, "user_metadata", None) or {}

    return {
        "supabase_user_id": str(user.id),
        "email": email.strip().lower(),
        "name": (metadata.get("full_name") or metadata.get("name") or "").strip(),
        "college": (metadata.get("college") or "").strip(),
    }


def get_or_sync_supabase_user(identity: dict, name_override: str = None, college_override: str = None):
    """
    Handles a verified Supabase identity:
    1. If user already linked by supabase_user_id: update optional college/name if blank, return user & local token.
    2. If user exists with the same email but NO supabase_user_id:
       DO NOT auto-link. Return 409 status with a flag prompting user to provide legacy password.
    3. If new user: create new SQLite record with password_hash=NULL, return user & local token.
    """
    sub_id = identity["supabase_user_id"]
    email = identity["email"]
    name = (name_override or identity.get("name") or "").strip()
    college = (college_override or identity.get("college") or "").strip()

    with conn() as c:
        # 1. Check if supabase_user_id already exists in SQLite
        row = c.execute(
            "SELECT id, name, email, college FROM users WHERE supabase_user_id = ?",
            (sub_id,),
        ).fetchone()

        if row:
            # Update missing college or name if provided
            updated = False
            curr_name = row["name"] or ""
            curr_college = row["college"] or ""
            if name and not curr_name:
                curr_name = name
                updated = True
            if college and not curr_college:
                curr_college = college
                updated = True
            if updated:
                c.execute(
                    "UPDATE users SET name = ?, college = ? WHERE id = ?",
                    (curr_name, curr_college, row["id"]),
                )
                c.commit()

            u = {
                "id": row["id"],
                "name": curr_name,
                "email": row["email"],
                "college": curr_college,
            }
            return {
                "status": "ready",
                "access_token": token(u["id"]),
                "user": u,
            }

        # 2. Check if a local account exists with the exact same email
        local_row = c.execute(
            "SELECT id, name, email, college, supabase_user_id, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if local_row:
            # If this local account is already linked to a different supabase identity
            if local_row["supabase_user_id"] and local_row["supabase_user_id"] != sub_id:
                raise HTTPException(
                    409,
                    "This email is already linked to a different authentication identity.",
                )
            # User exists in SQLite with password, require linking verification
            return {
                "status": "requires_linking",
                "message": "An existing SkillProof account was found for this email. Please verify your existing SkillProof password to securely link accounts.",
                "email": email,
                "has_password": bool(local_row["password_hash"]),
            }

        # 3. Completely new verified Supabase user: provision in SQLite
        cur = c.execute(
            """
            INSERT INTO users(name, email, password_hash, college, supabase_user_id)
            VALUES(?, ?, NULL, ?, ?)
            """,
            (name or "SkillProof Explorer", email, college, sub_id),
        )
        c.commit()
        uid = cur.lastrowid
        u = {
            "id": uid,
            "name": name or "SkillProof Explorer",
            "email": email,
            "college": college,
        }
        return {
            "status": "ready",
            "access_token": token(u["id"]),
            "user": u,
        }


def link_existing_account_with_supabase(identity: dict, password: str):
    """
    Securely links an existing SQLite user to the verified Supabase identity:
    1. Matches user by normalized email.
    2. Verifies legacy password against stored password_hash.
    3. Checks that neither this user nor this supabase_user_id is already bound to another account.
    4. Associates supabase_user_id with the existing SQLite user row (preserving user id and history).
    5. Returns the user and a valid session token.
    """
    sub_id = identity["supabase_user_id"]
    email = identity["email"]

    with conn() as c:
        # Check if this supabase_user_id is already linked to another local account
        already_linked = c.execute(
            "SELECT id FROM users WHERE supabase_user_id = ?",
            (sub_id,),
        ).fetchone()
        if already_linked:
            raise HTTPException(
                409,
                "This Supabase account is already associated with an account.",
            )

        row = c.execute(
            "SELECT id, name, email, password_hash, college, supabase_user_id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if not row:
            raise HTTPException(404, "No existing local account found for this email")

        if row["supabase_user_id"]:
            raise HTTPException(
                409,
                "This account is already linked to a Supabase identity.",
            )

        if not row["password_hash"]:
            raise HTTPException(
                400,
                "Account does not have a local password configured.",
            )

        if not pwd.verify(password, row["password_hash"]):
            raise HTTPException(401, "Incorrect SkillProof password. Account linking failed.")

        # Update SQLite user with supabase_user_id
        c.execute(
            "UPDATE users SET supabase_user_id = ? WHERE id = ?",
            (sub_id, row["id"]),
        )
        c.commit()

        u = {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "college": row["college"],
        }
        return {
            "status": "linked",
            "access_token": token(u["id"]),
            "user": u,
            "message": "Account successfully linked with Supabase.",
        }


def current(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        return None

    access_token = creds.credentials

    # First preserve support for existing local HS256 sessions.
    try:
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=["HS256"],
        )
        uid = int(payload["sub"])
    except (JWTError, ValueError, KeyError, TypeError):
        # If it is not a valid local token, verify it with Supabase Auth.
        if not (SUPABASE_URL and SUPABASE_KEY):
            raise HTTPException(401, "Invalid or expired authentication token")
        identity = verify_supabase_access_token(access_token)

        with conn() as c:
            row = c.execute(
                """
                SELECT id, name, email, college
                FROM users
                WHERE supabase_user_id = ?
                """,
                (identity["supabase_user_id"],),
            ).fetchone()

        if not row:
            raise HTTPException(
                401,
                "Supabase account is not linked to a SkillProof account",
            )

        return dict(row)

    with conn() as c:
        row = c.execute(
            "SELECT id, name, email, college FROM users WHERE id = ?",
            (uid,),
        ).fetchone()

    if not row:
        raise HTTPException(401, "Account not found")

    return dict(row)


def required(user=Depends(current)):
    if not user:
        raise HTTPException(401, "Sign in to access saved analyses")
    return user
