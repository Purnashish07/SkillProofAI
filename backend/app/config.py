import os
from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_FILE)

DEVELOPMENT_SECRET_KEY = "dev-secret-change-before-deployment"
SECRET_KEY = os.getenv("SECRET_KEY") or DEVELOPMENT_SECRET_KEY
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./skillproof.db")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def validate_production_secret_key() -> None:
    secret_key = os.getenv("SECRET_KEY", "").strip()
    if (
        len(secret_key) < 32
        or secret_key == DEVELOPMENT_SECRET_KEY
        or secret_key.lower().startswith(("replace-with-", "your-"))
    ):
        raise RuntimeError(
            "Production requires a unique SECRET_KEY of at least 32 characters."
        )
