# CareerPilot AI: Your Personal AI Career Guide

CareerPilot AI compares a resume with a job description and explains, in plain terms, which skills the job asks for, which your resume shows, which were **not found in your resume**, and what to learn first. It also provides a resume analyzer, learning roadmaps with progress tracking, cover-letter drafts, a job-application tracker, a dashboard, and a protected admin panel.

Everything runs for free on your own computer: **no paid AI API, domain, or hosting is required**. The AI model (Ollama) is optional; every core feature works without it using transparent rule-based algorithms, and results are always labelled by where they came from.

> Status honesty: see [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for what has and has not been tested, and what still needs manual setup.

## Features
- **Job Skill Intelligence**: extracts required / preferred / unclear skills and qualifications from a job description, lets you review and correct them, then compares with your resume using a documented, deterministic score (not a hiring prediction).
- **Resume analyzer**: PDF/DOCX upload with content validation, section detection, skill evidence, structure checks, wording suggestions, downloadable report. Scanned PDFs are detected and explained, not silently analysed.
- **Learning roadmaps**: prioritised skills, prerequisites, plain-language explanations, practice tasks, project ideas, effort *estimates*, official-docs links, saved progress.
- **Cover letters**: AI draft (if Ollama runs) or labelled template fallback; only facts from your resume/notes; edit, save, copy, download.
- **Application tracker**: CRUD, search, filter, sort, pagination, deadlines, CSV export.
- **Dashboard** with real data only; **Admin panel** with aggregate analytics, user disable/reactivate, audit log, health and AI status.
- Accounts: Argon2id passwords, email verification, password reset, cookie sessions with CSRF protection, rate limiting, account deletion.

There is intentionally **no interview feature** (the `INTERVIEWING` application status only tracks real applications).

## Tech stack
React + Vite + TypeScript + Tailwind, React Router, TanStack Query, React Hook Form + Zod, Recharts, Lucide.
FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, Argon2id, PyMuPDF, python-docx, pytest. Ollama (optional).

## What to install first
| Tool | Version | Needed for |
|---|---|---|
| Git | any recent | version control |
| Python | 3.11 or 3.12 | backend |
| Node.js | 20 LTS or newer (includes npm) | frontend |
| Docker Desktop | recent | local PostgreSQL (or install PostgreSQL 16 yourself) |
| Ollama | optional | local AI drafts and suggestions |

Ollama hardware note: the default model `llama3.2:3b` is roughly a 2 GB download and runs best with 8 GB+ RAM. On a CPU-only laptop a cover letter can take from tens of seconds to a couple of minutes. No GPU is required. If your machine struggles, set `AI_ENABLED=false`; nothing else is affected.

## Run it locally (Windows PowerShell)
```powershell
# 1. Database (from the project root)
docker compose up -d db

# 2. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements-dev.txt
copy .env.example .env
# Open .env and set SECRET_KEY. Generate one with:
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. Create the tables (first time only: generate the migration, then apply it)
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
# Keep the generated file in backend/alembic/versions and commit it to Git.

# 4. Create the first administrator (password is typed at a hidden prompt)
python -m app.scripts.create_admin --email you@example.com --name "Your Name" --role SUPER_ADMIN

# 5. Start the API (http://localhost:8000, API docs at /docs in development)
uvicorn app.main:app --reload
```
```powershell
# 6. Frontend (new terminal, from the project root)
cd frontend
npm install
npm run dev                            # http://localhost:5173
```
Open http://localhost:5173 and register. **Local email:** with `EMAIL_MODE=console` the verification and password-reset links are printed in the backend terminal inside a block marked `LOCAL DEVELOPMENT EMAIL`. Copy the link into your browser. (Never used in production.)

### Optional: local AI with Ollama
```powershell
# install from https://ollama.com, then:
ollama pull llama3.2:3b
ollama serve                            # skip if it already runs in the background
```
The admin panel (AI & health tab) shows whether the model is reachable. Change the model with `OLLAMA_MODEL` in `backend/.env`.

### Run the tests and the build
```powershell
cd backend;  pytest                     # backend tests (SQLite, isolated; never touches your real database)
cd frontend; npm test                   # frontend tests (Vitest)
cd frontend; npm run build              # type-check + production build
```

## Deploying publicly
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). It uses free tiers (and explains their limits and alternatives) and does not need a paid domain.

## Documentation
- [Architecture, database schema and API](docs/ARCHITECTURE.md)
- [Security and privacy checklist](docs/SECURITY.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Limitations, test status and resume blurb](docs/LIMITATIONS.md)

## Extending the skill taxonomy
Skills live in `backend/app/services/skills/taxonomy.json` (name, category, aliases, official-docs URL, effort estimate, prerequisites). Add entries there, or add custom skills from **Admin → Skills** without touching code. Ambiguous words (`go`, `r`, `c`, `excel`) are deliberately not bare aliases; use unambiguous ones like `golang`.

## Project layout
```
careerpilot-ai/
  backend/app/{api,core,db,models,schemas,services,ai,scripts,tests}, alembic/
  frontend/src/{components,pages,layouts,hooks,services,types,schemas,utils,tests}
  docs/  docker-compose.yml  .gitignore  README.md
```
