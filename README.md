# AppContributor

A task marketplace where startups post technical blockers and contributors submit practical fixes for payouts.

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: static HTML/CSS/JS (served by Vercel)
- Payments: Stripe + PayPal webhook scaffolding

## Project layout

```text
backend/
  api_server.py
  alembic/
  scripts/
frontend/
  index.html
  views/
    dashboard.html
    tasks.html
    onboarding.html
    startup-onboarding.html
    admin-signin.html
  css/
  js/
  assets/
scripts/
  inject-api-base-url.mjs
  inject-posthog-browser-token.mjs
```

## Local run

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m alembic -c alembic.ini upgrade head
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
python -m http.server 5500
```

Open `http://127.0.0.1:5500`.

## Vercel build env

- `APP_API_BASE_URL` (or `VERCEL_APP_API_BASE_URL`) -> your backend URL including `/api`
- `POSTHOG_BROWSER_PROJECT_TOKEN` (optional)

`npm run build` injects these into:

- `frontend/js/api-config.js`
- `frontend/js/posthog.browser.js`

## License

MIT
