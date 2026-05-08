# AppContributor — Roadmap

Short living document so new chats (or collaborators) know **where things stand** and **what to do next**. Update this when you ship or reprioritize.

---

## Done (high level)

- **Frontend**: Premium medical-style UI; landing hero; contributor vs startup entry; hidden admin (`?ops=1`); auth modal (sign in / create account tabs); onboarding (dropdowns for country, education, experience); startup onboarding + company fields; dashboard (contributor / startup / admin); task cards + modal; wallet + receipts (local); disputes UI + admin responses; profile photo upload (local); live landing metrics from API.
- **Backend**: FastAPI + SQLite; tasks, submissions, payouts, webhooks, receipts, task import URL; auth (signup/login/me); `profile_completed` on users; startup model + registration + admin review; startup task requests + admin review; metrics overview endpoint; contributor-only submissions with token + role checks.
- **Rules**: UI spacing consistency rule in `.cursor/rules/`.

---

## Next (recommended order)

### 1. Publish startup-approved tasks to the catalog

When an admin approves a startup task request with **publish**, create or update a real `TaskRecord` so contributors see it on `/api/tasks` and in the app. Today the request is tracked; the public task list may not reflect it yet.

### 2. Harden remaining admin-only APIs

Add the same pattern as submissions: `Authorization: Bearer` + `role === admin` (and optionally `profile_completed`) for:

- `PATCH /api/payout-requests/{id}`
- `POST /api/tasks/import-url`
- Startup registration review + task request review (partially there; align all admin writes)

### 3. Sync “profile completed” everywhere

Ensure `GET /api/auth/me` is used on `tasks.html` / `dashboard.html` on load so the session matches the server if localStorage was edited. Optionally refresh session after onboarding.

### 4. Profile picture on the server

Move avatar from `localStorage` only to an API (e.g. base64 or multipart upload) tied to `user_id`, with size limits and optional image processing.

### 5. Contributor submissions from the real DB

Either list submissions from the backend for the dashboard or keep mirroring to `localStorage` but document the single source of truth. Long-term: submissions API + admin review API on DB rows only.

### 6. Startup task publish → `startup_name` on tasks

If tasks are created from requests, set `startup_name` from `StartupRecord.company_name` (may require a column on `tasks` or embedding in description until a column exists).

### 7. Ops / compliance polish

Rate limits on auth; password reset flow; audit log table for admin actions; clearer error messages for locked onboarding.

---

## How to use this file

At the start of a **new** Cursor chat, paste or `@`-mention:

`ROADMAP.md`

…and one sentence on what you want that session to focus on (e.g. “implement step 1 only”).
