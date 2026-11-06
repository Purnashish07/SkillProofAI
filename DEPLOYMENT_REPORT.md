# SkillProofAI Deployment Report

**Status: NOT DEPLOYED.** No Vercel or Render resource was created, no paid action was taken, and no public application URL has been tested. The owner approved a free, guest-only deployment; provider dashboard sign-in is still required. The selected Render configuration has no persistent disk, so guest-only use and data loss on restart/redeploy are known limitations.

## Hosting plan (prepared, not provisioned)

- **Frontend:** Vercel static Vite project; project root `frontend`, install `npm ci`, build `npm run build`, output `dist`.
- **Backend:** Render Blueprint in `render.yaml`; free Python 3.11.9 service, root `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/api/health`.
- **Data:** SQLite at `sqlite:///./skillproof.db` on Render's ephemeral filesystem. This is guest-only: no accounts or analysis history are expected to persist, and files/database contents can be lost on restart or redeploy. Do not enter real personal data. Persistent authenticated history would require a separately approved paid durable-storage option.
- **Costs:** The prepared Render service uses the free plan and has no persistent disk. No paid resource, charge, or subscription was authorized or created.
- **Configuration:** `frontend/vercel.json` includes a static SPA fallback. Production builds fail unless `VITE_API_URL` is provided, preventing accidental production bundles that default to localhost.

## Live URLs

| Component | Public URL | Result |
|---|---|---|
| Frontend | Not assigned | Not deployed; Vercel sign-in required |
| Backend | Not assigned | Not deployed; Render sign-in required |
| Backend health check | Not available | Must return HTTP 200 from the actual deployed `/api/health` endpoint |
| Demo video | Not recorded or published | See `demo_video/` production materials |

No hosting or demo URLs are fabricated.

## Environment variable names

Set values in the hosting providers' private environment-variable settings only. Never commit production `.env` files.

**Render**

- `ENVIRONMENT` = `production`
- `SECRET_KEY` = unique random value, at least 32 characters; Blueprint requests provider-generated value
- `DATABASE_URL` = `sqlite:///./skillproof.db` (ephemeral; guest-only)
- `ALLOWED_ORIGINS` = exact HTTPS Vercel production origin (set after it is assigned; no wildcard)
- `JWT_EXP_SECONDS` = `86400`
- `SUPABASE_URL` and `SUPABASE_KEY` = optional until a Supabase project is configured; required to enable Supabase Auth
- `PORT` = supplied automatically by Render

**Vercel**

- `VITE_API_URL` = actual HTTPS Render service origin; required at build time
- `VITE_SUPABASE_URL` = optional until Supabase is configured
- `VITE_SUPABASE_PUBLISHABLE_KEY` = optional public/publishable Supabase key; required at build time only when enabling Supabase Auth

The Supabase URL and publishable key must refer to the same project in both services. Do not set a Supabase service-role key or backend signing secret in a `VITE_` variable. The generated Render `SECRET_KEY` must not be copied to Vercel.

## Audit and local verification

- Local source audit matched GitHub `main` at commit `63fcf84` before deployment-preparation changes. The reviewed release and demo changes are committed and pushed to `main` as `7b857cd`.
- Backend tests: **40 passed** across three modules (`test_isolated_endpoints.py`: 10, `test_suite.py`: 19, `test_cors_production.py`: 11). These include the oversized-upload regression test. `compileall` and `pip check` passed.
- Frontend `npm ci` had previously passed with 0 reported vulnerabilities. A Vite 8.3.5 production build passed with a test-only HTTPS API origin. A build using `http://localhost:8000` failed as intended. No localhost/loopback strings were found in the generated production JavaScript bundle.
- The fictional PDF was generated, parsed as a one-page document, and uploaded to the local FastAPI guest endpoint using an isolated temporary database. The real API response contained 5 demonstrated, 3 partial, and 1 missing skill. This is a local integration test, not a public-service test.
- No Render or Vercel deployment/build has been run.
- No public browser-console, endpoint, guest upload, authentication, saved-history, PDF-report, or secret-exposure tests have been run.
- No deployment secrets were requested or exposed in chat.

## Feature verification status

| Feature | Local evidence | Public production status |
|---|---|---|
| Guest Explorer and PDF upload | Backend API tests; local FastAPI upload of the synthetic PDF passed using an isolated temporary database | Not tested against a public service |
| PDF parsing and analysis/classification | The local FastAPI guest upload extracted the synthetic PDF and returned all three evidence categories | Not tested against a public service |
| Evidence coverage, gaps, action plan, interview preparation | Returned by the existing analysis endpoint and covered by backend tests | Not tested |
| Authentication and profile | Backend tests cover local auth, Supabase sync/link logic, and profile updates | Not tested; requires the owner's Supabase project to enable new-account sign-in |
| Saved history and PDF report | Backend tests exercise signed-in history and ReportLab export | Not tested; requires an account and persistent production database |
| CORS, production secret validation | Local tests cover configured origins, invalid origins, wildcards, and missing/placeholder signing keys | Not tested against a hosting origin |
| No localhost API in production bundle | HTTPS-only API-origin build validation passed; generated JavaScript bundle scan found no localhost/loopback URL | Not applicable until a deployed-origin build exists |

## Manual steps blocking deployment

1. Sign in to Render and Vercel through their official dashboards using your own account session; do not send passwords, recovery codes, or API tokens in chat.
2. Link the Render Blueprint to `Purnashish07/SkillProofAI` and inspect the free service configuration. Render should generate `SECRET_KEY`; set a random `ALLOWED_ORIGINS` value after the frontend domain is known.
3. Import the GitHub project into Vercel with root directory `frontend`. Once the Render HTTPS origin is assigned, set `VITE_API_URL` in the Vercel project before its production build. Select the actual Vercel-assigned domain, then configure Render's exact `ALLOWED_ORIGINS`.
4. This deployment is guest-only and uses ephemeral SQLite. Do not configure production user data, saved history, or report-export expectations without a separate durable database and explicit paid-resource approval.
5. Confirm provider deployments, logs, builds, and health checks through the logged-in dashboards. Then run the public feature/console/security tests and replace this report's pending statuses with measured results.

Public deployment still requires provider sign-in; no live host or public URL exists yet.
