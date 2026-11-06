import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import DATABASE_URL

DB = DATABASE_URL.replace("sqlite:///", "", 1)


@contextmanager
def conn():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            college TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            role_title TEXT,
            resume_name TEXT,
            result_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)

        columns = {
            row["name"]
            for row in c.execute("PRAGMA table_info(users)").fetchall()
        }

        if "supabase_user_id" not in columns:
            c.execute("ALTER TABLE users ADD COLUMN supabase_user_id TEXT")

        c.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_supabase_user_id
            ON users(supabase_user_id)
        """)

        c.commit()
