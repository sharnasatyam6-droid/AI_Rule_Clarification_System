# Rulebook — AI Rules Clarity Checker

**Team:** Nexora · **Project:** AI Synergy, IIIT Gwalior

Rulebook is a policy directory and evidence-grounded AI-use policy checker.

## Technology stack
- Frontend: plain HTML, CSS, and vanilla JavaScript
- Backend: Python 3.11+ with FastAPI
- Database: PostgreSQL on Neon, using psycopg 3
- Hosting: Vercel Python Function at `api/index.py` (verify runtime support during deployment)
- Source control: GitHub

## Features
- Search and browse published policies.
- Five built-in scenarios and a custom situation field.
- Three results: **Allowed by the provided policy**, **Not allowed by the provided policy**, or **Unclear — Ask the Instructor**.
- Supporting excerpt, source policy, conditions, and safety disclaimer.
- Shared admin login, teacher search, add-teacher workflow, and create/edit/publish/delete policy management.
- Draft and published policy states.
- Responsive frontend; server-side validation and signed HttpOnly admin cookie.
- Sample policy text is labelled **DEMONSTRATION ONLY — not an official course rule**.

## Run locally
1. Install Python 3.11+.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # macOS/Linux
   source .venv/bin/activate
   ```
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set the variables below. Do not commit secrets.
5. Apply `db/schema.sql` to Neon or confirm that the existing tables match the schema.
6. Run `uvicorn backend.main:app --reload --port 8000`.
7. Open http://localhost:8000.

## Environment variables
- `DATABASE_URL`: Neon PostgreSQL connection string with TLS enabled.
- `ADMIN_USERNAME`: shared admin username.
- `ADMIN_PASSWORD`: shared admin password.
- `ADMIN_SESSION_SECRET`: random secret of at least 32 characters.
- `APP_ORIGIN`: optional local CORS origin (default `http://localhost:8000`).

Generate a secret with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Deploy to Vercel
1. Import this repository into Vercel and set the project root to the repository root.
2. Add `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_SESSION_SECRET` as server-side environment variables.
3. Deploy using the Python runtime and the routing configuration in `vercel.json`.
4. Verify `/health`, `/api/policies`, admin login, teacher management, and the complete policy-check flow. Do not assume deployment is working until these checks pass.
5. If the Python runtime is unavailable or static assets are not included by the Vercel builder, host FastAPI on a Python-friendly host and configure the frontend/API origin accordingly.

## Safety and limitations
The checker is a conservative deterministic evidence-matching baseline, **not an LLM or an official academic authority**. It should be evaluated against a reviewed test set before real use. Missing a prohibition is not evidence of permission; ambiguous or unsupported cases should be escalated to the instructor. Demo policies are fictional and must not be presented as official institutional rules.

## Database
The schema and fictional seed data are in `db/schema.sql`. For an existing database, review schema differences and do not blindly reset production data.
