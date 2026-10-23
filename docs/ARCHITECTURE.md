# Architecture, database and API

## Overview
```
Browser (React SPA)  --/api/v1-->  FastAPI  --SQLAlchemy-->  PostgreSQL
                                     |--> services/skills (pure Python engine)
                                     |--> ai/ provider interface --> Ollama (optional)
                                     |--> services/storage (private local folder)
```
One backend, one database, one SPA. No microservices.

**Same-origin API.** The browser always calls `/api/v1/...` on its own origin. In development Vite proxies `/api` to FastAPI; in production the host rewrites `/api` to the backend. This keeps session cookies first-party, so no CORS or third-party-cookie problems.

## Backend layers
- `api/routes/*`: HTTP only (validation, auth dependencies, response shaping).
- `core/`: config (fails fast on unsafe production settings), security (Argon2id, token hashing), deps (sessions, CSRF, role checks, ownership helper), rate limiting, error handling.
- `services/skills/`: **the Job Skill Intelligence engine**, pure Python with no web/DB imports, so it is unit-tested in isolation:
  - `taxonomy.py`: alias normalisation and word-boundary matching (no substring false positives).
  - `jd_parser.py`: sections + sentence cues -> required / preferred / uncertain, with the reason recorded.
  - `resume_parser.py`: sections, skill evidence per section, structure checks.
  - `comparison.py`: scoring and explanation.
- `services/roadmap.py`, `cover_letter.py`, `document_text.py`, `ai_features.py`, `storage.py`, `email.py`, `audit.py`.
- `ai/provider.py`: `LLMProvider` interface; `OllamaProvider` is the default. Business code calls `get_provider()`; adding another provider means one new class.

## How the score works
`score = 100 x sum(weight x credit) / sum(weight)`
- weight: required 3, unclear 2, preferred 1
- credit: shown in projects/experience 1.0, listed only in a skills section 0.6, not found 0
The response includes the formula, weights, earned points and a disclaimer. It measures how much of the posting's wording your resume text supports; it is not a probability of an interview or offer, and "not found" is not proof you lack a skill. Users can correct requirement levels, and the score is recomputed.

## AI behaviour and safety
- Rule-based extraction/scoring never uses a model, and results are never presented as AI output.
- AI is used only for cover-letter drafts and optional resume wording suggestions, labelled as such.
- Documents and job descriptions are fenced as untrusted data in prompts; fence tags inside them are stripped.
- Output is validated: length bounds, leaked-instruction patterns, **numbers/percentages must already appear in the inputs**, JSON shape checks, suggestions must quote a real resume line. On any failure the app falls back to the deterministic template.
- Every AI call is logged (feature, model, success, duration, short error) in `ai_usage_records`; prompts and documents are never stored there.

## Database schema (PostgreSQL, UUID keys, `created_at`/`updated_at` where relevant)
| Table | Purpose / notable constraints |
|---|---|
| users | unique lowercase email, Argon2id hash, role CHECK (USER/ADMIN/SUPER_ADMIN), is_active, email_verified_at |
| email_verification_tokens, password_reset_tokens | SHA-256 **hash** only, expiry, `used_at` (single use), FK CASCADE |
| sessions | hashed session token, expiry, `revoked_at`, user agent |
| resumes | owner, filename, type, size, extracted text, optional private stored file name |
| resume_analyses | JSON result (sections, skills with evidence, warnings, suggestions); AI suggestions kept in a separate column |
| job_descriptions | title, company, location, level, text |
| job_analyses | links job + resume; extracted JSON, user-corrected requirements, comparison JSON, score |
| skill_taxonomy, skill_aliases | seeded from `taxonomy.json`; admin-added skills flagged `is_custom`; alias unique |
| learning_roadmaps | one per analysis (UNIQUE) |
| roadmap_items | status CHECK, priority CHECK, tasks JSON with done flags, `completed_at` |
| cover_letters | content, source (ai / fallback_template / user_edited), model name |
| job_applications | status CHECK (SAVED, APPLIED, ASSESSMENT, INTERVIEWING, OFFER, REJECTED, WITHDRAWN); indexes on (user, status) and (user, deadline) |
| audit_logs | actor (SET NULL on delete), action, target, metadata (never content) |
| ai_usage_records | AI request metrics |
| error_events | request id, method, path, exception type (no bodies) |

All user-owned tables reference `users.id` with `ON DELETE CASCADE`, so account deletion removes every row; stored files are deleted explicitly. There is no `notifications` table (not implemented), and no interview tables.

Migrations: Alembic (`backend/alembic`). `env.py` reads `DATABASE_URL` and imports all models; generate the first migration with `alembic revision --autogenerate` (see README), then `alembic upgrade head`.

## API (all under `/api/v1`, OpenAPI at `/docs` in development)
Unsafe methods require the `X-CSRF-Token` header (value of the `cp_csrf` cookie).
| Area | Endpoints |
|---|---|
| Health | `GET /health`, `GET /health/ready` |
| Auth | `POST /auth/register, verify-email, resend-verification, login, logout, forgot-password, reset-password, change-password`; `GET /auth/me` |
| Profile | `GET/PATCH/DELETE /users/me` |
| Resumes | `POST /resumes` (multipart), `GET /resumes`, `GET /resumes/{id}`, `GET /resumes/{id}/download`, `GET /resumes/{id}/report`, `POST /resumes/{id}/ai-suggestions`, `DELETE /resumes/{id}` |
| Job analysis | `POST /job-analyses/extract` (no save), `POST /job-analyses`, `GET /job-analyses`, `GET /job-analyses/{id}`, `PATCH /job-analyses/{id}/requirements`, `GET .../report`, `DELETE` |
| Roadmaps | `POST /roadmaps`, `GET /roadmaps`, `GET /roadmaps/{id}`, `PATCH /roadmaps/{id}/items/{item_id}`, `DELETE /roadmaps/{id}` |
| Cover letters | `POST /cover-letters/generate`, `GET /cover-letters`, `GET/PATCH/DELETE /cover-letters/{id}`, `GET .../download` |
| Applications | `POST/GET /applications` (q, status, sort, order, page), `GET /applications/summary`, `GET /applications/export.csv`, `GET/PATCH/DELETE /applications/{id}` |
| Dashboard | `GET /dashboard` |
| Admin (ADMIN+) | `GET /admin/overview, users, users/{id}, audit-logs, ai, errors, health, taxonomy`; `POST /admin/users/{id}/disable|reactivate`, `POST /admin/taxonomy` |

Errors use one shape: `{"error": {"code", "message", "details?", "request_id?"}}`. Production responses never include stack traces.
