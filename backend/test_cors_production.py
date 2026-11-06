import os
import sys
import importlib
from pathlib import Path
import pytest
import httpx
from httpx import ASGITransport

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_SECRET_KEY = "test-only-secret-key-not-for-real-use-1234567890"


def load_app(
    env: str,
    allowed_origins: str | None = None,
    secret_key: str | None = TEST_SECRET_KEY,
):
    """Load the FastAPI app with given environment variables.
    Returns a tuple (app, exception). If loading succeeds, exception is None.
    """
    os.environ["ENVIRONMENT"] = env
    if secret_key is None:
        os.environ.pop("SECRET_KEY", None)
    else:
        os.environ["SECRET_KEY"] = secret_key
    if allowed_origins is not None:
        os.environ["ALLOWED_ORIGINS"] = allowed_origins
    else:
        os.environ.pop("ALLOWED_ORIGINS", None)

    # Ensure the module is re-imported fresh
    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    try:
        module = importlib.import_module("app.main")
        return module.app, None
    except Exception as exc:
        return None, exc


@pytest.fixture(autouse=True)
def cleanup_env():
    yield
    # Restore dev environment
    os.environ["ENVIRONMENT"] = "development"
    os.environ.pop("ALLOWED_ORIGINS", None)
    os.environ.pop("SECRET_KEY", None)
    if "app.main" in sys.modules:
        del sys.modules["app.main"]


@pytest.mark.asyncio
async def test_dev_defaults_load_success():
    app, err = load_app("development")
    assert err is None, f"App failed to load in dev mode: {err}"
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.options(
            "/api/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.asyncio
async def test_production_with_valid_origins():
    allowed = "https://frontend.example.com"
    app, err = load_app("production", allowed)
    assert err is None, f"App failed to load in prod mode: {err}"
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Trusted origin
        resp = await client.options(
            "/api/health",
            headers={"Origin": allowed, "Access-Control-Request-Method": "GET"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == allowed

        # Untrusted origin
        untrusted_resp = await client.options(
            "/api/health",
            headers={"Origin": "https://attacker.evil.com", "Access-Control-Request-Method": "GET"},
        )
        assert untrusted_resp.headers.get("access-control-allow-origin") != "https://attacker.evil.com"


@pytest.mark.asyncio
async def test_production_multiple_origins():
    origins = "https://skillproof.app, https://admin.skillproof.app"
    app, err = load_app("production", origins)
    assert err is None, f"App failed to load: {err}"
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp1 = await client.options(
            "/api/health",
            headers={"Origin": "https://skillproof.app", "Access-Control-Request-Method": "GET"},
        )
        assert resp1.headers.get("access-control-allow-origin") == "https://skillproof.app"

        resp2 = await client.options(
            "/api/health",
            headers={"Origin": "https://admin.skillproof.app", "Access-Control-Request-Method": "GET"},
        )
        assert resp2.headers.get("access-control-allow-origin") == "https://admin.skillproof.app"


def test_production_missing_allowed_origins_raises():
    app, err = load_app("production", None)
    assert app is None
    assert isinstance(err, RuntimeError)
    assert "ALLOWED_ORIGINS must be set" in str(err)


def test_production_empty_allowed_origins_raises():
    app, err = load_app("production", "")
    assert app is None
    assert isinstance(err, RuntimeError)
    assert "ALLOWED_ORIGINS cannot be empty" in str(err)


def test_production_whitespace_allowed_origins_raises():
    app, err = load_app("production", "   ,   ")
    assert app is None
    assert isinstance(err, RuntimeError)
    assert "ALLOWED_ORIGINS cannot be empty" in str(err)


def test_malformed_origin_raises():
    app, err = load_app("production", "not-a-valid-url")
    assert app is None
    assert isinstance(err, RuntimeError)
    assert "Malformed origin" in str(err)


def test_wildcard_with_credentials_raises():
    app, err = load_app("production", "*")
    assert app is None
    assert isinstance(err, RuntimeError)
    assert "Wildcard origin" in str(err)


@pytest.mark.parametrize(
    "secret_key",
    [None, "short", "replace-with-a-random-secret-that-is-long-enough"],
)
def test_production_requires_a_real_secret_key(secret_key):
    app, err = load_app("production", "https://frontend.example.com", secret_key)
    assert app is None
    assert isinstance(err, RuntimeError)
    assert "Production requires a unique SECRET_KEY" in str(err)
