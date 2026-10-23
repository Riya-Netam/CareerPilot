# Security and privacy checklist

Legend: **Done** = implemented in code; **Tested** = covered by an automated test that was written (see LIMITATIONS for what was actually executed); **You must do** = needs action at deployment.

| Area | Status |
|---|---|
| Argon2id password hashing, rehash on login, timing-equalised unknown-email login | Done, Tested |
| Password policy (10+ chars, letters and numbers) | Done, Tested |
| Verification/reset tokens: random, expiring, single use, stored as SHA-256 hashes | Done, Tested |
| Generic responses for register / forgot password / resend (no account enumeration) | Done, Tested |
| Cookie session: HttpOnly, Secure (configurable), SameSite, server-side revocation, expiry | Done, Tested |
| CSRF: double-submit token required on every state-changing authenticated request | Done, Tested |
| Rate limiting on register, login, verify, resend, forgot, reset, change/delete password, upload, AI, analysis | Done, Tested (login). In-memory, per process |
| Ownership checks on every user-owned object (404, not 403, to avoid leaking existence) | Done, Tested |
| Roles enforced in the backend (dependency on the whole admin router); no API to change roles; admin bootstrap only through CLI | Done, Tested |
| Admins cannot disable themselves, other admins (unless SUPER_ADMIN) or SUPER_ADMINs; disabling revokes sessions; all audited | Done, Tested |
| Admin views expose aggregates only; no resume, letter, note or token content | Done, Tested |
| Upload safety: size cap (read bounded), magic-byte type detection, DOCX unpack-size limit, PDF page limit, password-protected PDF refused, scanned PDF reported, generated storage names, per-user folders, no public folder | Done, Tested (DOCX/invalid). PDF extraction path not executed in the build sandbox |
| Retention control: `STORE_ORIGINAL_FILES=false` keeps only extracted text | Done |
| Prompt injection: fenced untrusted data, system guard, output validation, no AI output used for authorisation or executed | Done, Tested |
| CSV export formula-injection neutralised | Done, Tested |
| Safe DB access (SQLAlchemy parameters), DB CHECK/UNIQUE/FK constraints, cascade deletion | Done, Tested |
| Production config guard (refuses weak SECRET_KEY, insecure cookies) | Done |
| Error handling: uniform JSON, no stack traces in production, request ids, errors recorded without bodies | Done |
| Logs: method, path, status, timing only. No passwords, tokens, resumes or letters. Dev-only email links printed in a marked block, never in production | Done |
| Security headers on API responses (nosniff, frame deny, no-referrer, no-store); API docs disabled in production | Done |
| CORS limited to configured origins | Done |
| Account deletion removes all rows (cascade) and stored files | Done, Tested |
| HTTPS | **You must do**: provided by the host; set `COOKIE_SECURE=true` |
| Secrets in env vars only; `.env` ignored by Git | **You must do**: set production values |
| Content-Security-Policy for the frontend host | **You must do** (add headers on your static host) |
| Dependency scanning (`pip-audit`, `npm audit`), pinned lockfiles | **You must do** |
| Multi-instance rate limiting, backups, monitoring/alerting | **You must do** if you scale beyond a demo |
| Independent security review / penetration test | Not done |

## Privacy notes
- Resume text is stored in the database so analyses can be recomputed when you correct requirements. Deleting a resume deletes its text, analyses and file.
- Resumes are sent to no external service. AI runs only against your own Ollama instance. Adding an external provider means implementing `LLMProvider`; do that only with clear user consent.
- Email addresses are stored lowercase. Audit logs record who did what, never the content involved.
