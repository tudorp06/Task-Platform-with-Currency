# Private Beta V1.0 Release Runbook

## 1) Secrets and Environment
- Copy `backend/.env.example` to `backend/.env` for local/dev setup.
- Keep production secrets only in host-managed secret storage.
- Rotate any previously used bootstrap/admin credentials before beta launch.

## 2) Database and Migration Path
- Current local runtime uses SQLite for development.
- Private beta target: managed Postgres with SQLAlchemy-compatible URL.
- Run pre-release migration in staging first, then production.
- Keep one rollback snapshot before each migration.

## 3) Backup and Restore Drill
- Daily DB snapshots are mandatory in beta.
- Run a restore drill at least once per week into a non-production instance.
- Record restore duration and checksum/row-count parity.

## 4) Release Gates (Go/No-Go)
- Backend syntax check: `python -m py_compile backend/api_server.py`.
- Auth/RBAC smoke test: signup/login/profile-complete/admin-only routes.
- Payment safety smoke test: Stripe signature rejection + duplicate webhook replay.
- Privacy checklist pass: `PRIVACY_SECURITY_CHECKLIST.md` has no open critical items.

## 5) Rollback
- Keep last known-good backend image/build artifact available.
- If critical auth/payment regression appears, roll back immediately.
- Restore database from latest pre-release snapshot only when data integrity is affected.
