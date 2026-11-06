# SkillProofAI

SkillProofAI is a career-readiness tool that compares a resume with a job description and shows where the resume contains direct, partial, or no evidence for requested skills. It is decision support for candidates, not a hiring score or a prediction of employment.

## Features

- Extracts selectable text from PDF resumes and matches it against a job description.
- Shows evidence snippets and the signals used for each skill classification.
- Suggests small portfolio projects and interview questions for skills with gaps.
- Creates downloadable PDF reports for saved analyses.
- Provides saved analysis history for signed-in users and exploratory, self-reported college-level aggregates.
- Supports legacy SkillProof tokens and optional Supabase authentication.

The analysis engine is deterministic and taxonomy-based; it does not call a generative AI service. Scanned/image-only PDFs are not OCR-processed.

## Architecture

```text
React + Vite browser app
          |
          | HTTP / JSON, PDF uploads
          v
FastAPI backend ---- Supabase Auth (optional)
          |
          v
SQLite database (created locally)
```

The frontend calls the FastAPI API. The backend parses PDF text, creates evidence results, and stores signed-in users' analyses in SQLite. Supabase is used only when its frontend and backend settings are supplied; local demo analysis does not require Supabase.

## Technology

- Frontend: React 18, Vite, JavaScript, CSS, Lucide React
- Backend: Python, FastAPI, Uvicorn, Pydantic
- Storage: SQLite
- PDF handling: PyMuPDF and ReportLab
- Authentication: bcrypt password hashes, HS256 local tokens, optional Supabase Auth
- Tests: pytest, pytest-asyncio, HTTPX

## Project layout

```text
SkillProofAI_GitHub_Release/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── engine.py
│   │   ├── main.py
│   │   └── security.py
│   ├── .env.example
│   ├── requirements.txt
│   ├── test_cors_production.py
│   ├── test_isolated_endpoints.py
│   └── test_suite.py
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── style.css
│   │   └── supabase.js
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── .gitignore
├── FINAL_RELEASE_AUDIT.md
├── README.md
└── start_local.ps1
```

`.venv`, `node_modules`, build output, local environment files, and SQLite data are local/generated files and are not part of the release source.

## Requirements

- Windows PowerShell
- Python 3.10 or newer
- Node.js 20.19+ or 22.12+, with npm

## Install and run

From the project root in PowerShell:

```powershell
python --version
node --version
npm --version
.\start_local.ps1
```

The startup script creates the project-local `.venv` when needed, installs backend dependencies if the requirements have changed or imports are missing, runs `npm ci` if frontend dependencies are absent, and opens the API and Vite development server in separate consoles. The SQLite database is created locally under `backend\` on first backend startup; no database is shipped.

Open:

- Frontend: http://127.0.0.1:5173
- API health: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

Without frontend Supabase settings, the app still starts and supports guest analysis. Supabase sign-in/sign-up is disabled; legacy sign-in is available for accounts that already exist. No demo user account or local database is included.

## Environment configuration

Copy only the templates you need. Never commit the resulting `.env` files.

```powershell
Copy-Item backend\.env.example backend\.env
```

For local development, set `SECRET_KEY` to a unique random value before using saved accounts. For example, generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Replace the placeholder `SECRET_KEY` in `backend\.env` with the generated value. The backend loads that file when it starts. `DATABASE_URL` defaults to a SQLite file in the backend working directory. `SUPABASE_URL` and `SUPABASE_KEY` are only needed for Supabase-backed authentication.

To enable frontend Supabase authentication, copy `frontend\.env.example` to `frontend\.env` and replace both Supabase placeholders with your project URL and **publishable** key:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

`VITE_SUPABASE_PUBLISHABLE_KEY` is bundled into browser code; only a Supabase publishable/anon key belongs there. Never put a Supabase service-role key, JWT signing key, or other server secret in a `VITE_` variable. Restart Vite after changing frontend environment variables. Do not expose the development server to an untrusted network.

For production, configure a unique `SECRET_KEY` of at least 32 characters and an explicit, non-wildcard `ALLOWED_ORIGINS` list. The backend refuses to start in production with a missing, short, or template/development secret. This repository does not include production deployment configuration.

## Tests and production build

The startup script installs Python test dependencies. To prepare them without launching the servers:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Run each backend module in its own command. Each suite uses a temporary test database:

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend\test_isolated_endpoints.py
.\.venv\Scripts\python.exe -m pytest -q backend\test_suite.py
.\.venv\Scripts\python.exe -m pytest -q backend\test_cors_production.py
```

Install and build the frontend:

```powershell
Push-Location frontend
npm ci
npm run build
Pop-Location
```

## Security and privacy limitations

- Resume analysis is lexical and taxonomy-based; it can miss synonyms, context, and skills shown in image-only documents. Review every result.
- The application is a prototype, not a hiring decision system, and college aggregates are based on self-reported profile data.
- Local HS256 tokens are stored in browser local storage. Production use requires a deployment-specific threat model, transport security, key management, monitoring, and abuse/rate limiting controls.
- SQLite is suitable for local development; this repository does not provide production database, backup, or deployment automation.
- Never upload resumes or personal information unless you understand and accept the environment in which the app is running.

## Screenshots

No screenshots are included in this release yet. Add genuine screenshots here when they are available.

## Author

Project team: **NOVARYTHM**  
GitHub repository owner: **Purnashish07**
