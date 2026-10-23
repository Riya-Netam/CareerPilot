# Free-tier deployment guide

Nothing here has been deployed or verified by the author of this repository. Free tiers change, so **check each provider's pricing page before you start**. The numbers below were checked in October 2026.

## What works publicly, and what does not
- Public mode runs the **frontend, API and PostgreSQL** with all rule-based features: resume analysis, skill extraction, scoring, roadmaps, template cover letters, tracker, dashboard, admin.
- **Ollama will not be available** on free hosting (it needs a machine with enough RAM that stays online). Set `AI_ENABLED=false`. The app labels cover letters as "Template (no AI used)".
- For a **faculty demo with AI**, run everything locally (README). If you point a public site at Ollama on your laptop, the laptop must stay powered, online and reachable, which is not a reliable plan; don't do it for anything people depend on.

## Recommended free setup
| Part | Option | Free-tier facts to know (verify) |
|---|---|---|
| Database | **Neon** (PostgreSQL) | Free plan: 100 CU-hours and 0.5 GB per project, scales to zero after 5 minutes idle, so the first query after a pause is slower. |
| Backend | **Render** web service (Docker) | Free web services spin down after 15 minutes idle and take about a minute to wake; the instance has no persistent disk, so uploaded files would be lost on restart. |
| Frontend | **Vercel** (or Netlify / Cloudflare Pages) | Free hobby plans are meant for personal, non-commercial projects. Check the current terms. |
| Email | **Brevo** SMTP | Free plan: 300 emails/day, with Brevo branding on emails. Alternative: Resend (3,000/month, 100/day) but it needs a domain you own. |

Do **not** use Render's free PostgreSQL for anything you want to keep: it expires 30 days after creation (then deleted after a grace period). Use Neon instead.

If Render's cold starts are unacceptable, alternatives are Fly.io or Google Cloud Run (both may require a card and have their own free allowances). Check their terms before choosing.

## Steps
### 1. Push to GitHub
```powershell
git init; git add .; git commit -m "CareerPilot AI"
# create an empty GitHub repo, then:
git remote add origin https://github.com/YOU/careerpilot-ai.git; git push -u origin main
```
Make sure `backend/alembic/versions/` contains your generated migration before pushing (README step 3). `.env` files must not be committed.

### 2. Database (Neon)
Create a project, copy the connection string (it looks like `postgresql://user:pass@host/db?sslmode=require`). The app converts the prefix for you.

### 3. Backend (Render)
New > Web Service > your repo. Runtime **Docker**, root directory `backend`. Health check path `/api/v1/health`. The container runs `alembic upgrade head` and then starts the API.
Environment variables:
```
ENVIRONMENT=production
SECRET_KEY=<48+ random characters>
DATABASE_URL=<Neon connection string>
FRONTEND_URL=https://YOUR-APP.vercel.app
CORS_ORIGINS=https://YOUR-APP.vercel.app
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
TRUST_PROXY=true
AI_ENABLED=false
STORE_ORIGINAL_FILES=false
EMAIL_MODE=smtp
EMAIL_FROM=CareerPilot AI <your-verified-sender@example.com>
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=<from Brevo>
SMTP_PASSWORD=<from Brevo SMTP key>
```
(`STORE_ORIGINAL_FILES=false` because the free instance disk is not persistent; resumes are still analysed and their extracted text is stored in the database.) Verify the Brevo host/port and sender rules in Brevo's SMTP settings page.

### 4. Frontend (Vercel)
Import the repo, root directory `frontend`, framework Vite. Edit `frontend/vercel.json` and replace `YOUR-BACKEND-URL` with your Render URL (no trailing slash). The `/api` rewrite makes the browser see one origin, so cookies stay first-party. Deploy, then put the final Vercel URL into the backend's `FRONTEND_URL` and `CORS_ORIGINS`.

### 5. First administrator
Render's free tier may not offer a shell. Create the admin from your own computer against the Neon database without saving the URL to a file:
```powershell
cd backend; .\.venv\Scripts\Activate.ps1
$env:ENVIRONMENT="development"; $env:DATABASE_URL="<Neon connection string>"
python -m app.scripts.create_admin --email you@example.com --role SUPER_ADMIN
Remove-Item Env:DATABASE_URL
```

### 6. Verify the deployment (all of these must pass)
1. `https://YOUR-BACKEND/api/v1/health/ready` returns `{"status":"ready"}` (first call may take a minute).
2. Register with a real email; the verification email arrives; the link works; you can sign in.
3. Upload a DOCX resume, analyse a pasted job description, create a roadmap and a cover letter.
4. Sign in as admin: Admin > AI & health shows database OK and configuration checks.
5. Browser dev tools: the session cookie is `Secure` and `HttpOnly`.

## Known caveats
- If resume uploads fail through the Vercel rewrite (proxy size or timeout limits), either switch to a Render Static Site with a rewrite rule for `/api`, or set `VITE_API_BASE` to the backend URL with `COOKIE_SAMESITE=none` and exact `CORS_ORIGINS`; some browsers block third-party cookies, so the rewrite approach is preferred.
- Rate limits are per process and reset on restart.
- Free instances sleep; mention this to anyone you demo to, or open the site a minute early.
