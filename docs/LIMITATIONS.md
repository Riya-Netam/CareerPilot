# Limitations, test status and resume blurb

## What was actually executed when this project was generated
The build environment had **no internet access** and only Python 3.12, Node 22 and `python-docx` installed. Because FastAPI, SQLAlchemy, PostgreSQL, npm packages and Ollama could not be installed, the following is the honest status:

| Item | Status |
|---|---|
| Skill engine (taxonomy matching, JD parsing, resume parsing, comparison/score, roadmap, cover-letter fallback, DOCX extraction and file validation) | **18 automated tests written and run: 18 passed** (`app/tests/test_engine.py`) |
| AI output validation, prompt fencing, JSON parsing | Logic exercised in a stubbed run: passed. Tests written in `test_ai_validation.py`, not run under pytest |
| Python syntax of every backend file | Checked (compiles) |
| Backend API tests (auth, access control, flow, applications, admin, DB constraints) | **Written, NOT run** (51 test functions). They need `pip install -r requirements-dev.txt` |
| FastAPI app startup, Alembic migration, PostgreSQL behaviour, PDF extraction (PyMuPDF) | **Not run** |
| Frontend: TypeScript syntax | Parsed with `tsc` with no syntax errors. Full type-check **not possible** without packages |
| Frontend tests (Vitest) and production build | **Written / not run** |
| Docker build, Ollama calls, deployment | **Not run. Nothing has been deployed.** |

Expect to fix a small number of mistakes on first run (typical for code that has not met its dependencies). Run, in order: `pytest`, `npm run build`, `npm test`, and send me any errors.

## Known limitations
- Skill extraction is dictionary-based. It will miss skills not in the taxonomy and cannot understand negation ("no Java required"). Required/preferred detection relies on wording and headings; ambiguous cases are marked "unclear" by design.
- Experience years and degrees are shown for manual confirmation, not scored.
- Section detection expects headings on their own line; unusual resume designs (multi-column PDFs) may be read out of order.
- No OCR: scanned PDFs are rejected with an explanation.
- Rate limiting and the taxonomy cache are per process.
- No notifications feature, no background jobs.
- Alembic migration must be generated once on your machine (`--autogenerate`) because it could not be produced without a database.
- Frontend uses hand-written Tailwind components rather than shadcn/ui (the shadcn CLI needs network access). Recharts is used for the dashboard chart only.
- Resource links are official documentation homepages from the taxonomy; they were not link-checked.

## Still required for a public launch
HTTPS-hosted deployment and real SMTP, strong production secrets, backups, dependency audits, a Content-Security-Policy, monitoring, and a security review. See SECURITY.md and DEPLOYMENT.md.

## Resume / portfolio description
**CareerPilot AI** (React, TypeScript, FastAPI, PostgreSQL, Ollama): Full-stack career-guidance platform that compares resumes with job descriptions and explains skill gaps.
- Built an explainable skill-intelligence engine (alias-normalised taxonomy of ~100 skills, required/preferred classification with recorded reasons, transparent weighted scoring, resume evidence snippets).
- Implemented secure authentication (Argon2id, hashed single-use email/reset tokens, cookie sessions with CSRF protection, rate limiting) and role-based admin panel with audit logging and aggregate-only analytics.
- Designed provider-independent local-LLM integration (Ollama) with output validation against hallucinated figures, prompt-injection defences, and deterministic fallbacks so core features work offline.
- Modelled 17 PostgreSQL tables with Alembic migrations, cascading deletes and CHECK constraints; wrote automated tests for the engine, API, access control and UI flows.
(Edit this to match what you actually ran and verified.)
