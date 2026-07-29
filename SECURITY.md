# Security

## Supported versions

This is a small open-source utility. Security fixes apply to the latest
default branch.

## Reporting a vulnerability

Please do **not** open a public issue for security-sensitive reports.

Prefer:

1. A private GitHub security advisory on the repository, or
2. Contacting the maintainers privately via the contact method listed on the repo

Include steps to reproduce, impact, and any suggested fix if you have one.

## Scope notes

- Local SQLite and disk cache hold derived open data, not user accounts
- **Clerk / meter trial is UX-only.** Sign-in and the free distinct-meter cap live in
  the browser (`localStorage` + Clerk session). They do **not** authorize API access.
  Anyone can call `/api/meters` and `/api/meters/{id}` directly. Do not treat the
  frontend gate as confidentiality or paid-access control unless you add server-side
  auth and quotas.
- Production API hardening (implemented in `api/py/server.py`):
  - `CORS_ORIGINS` — comma-separated allowlist (defaults to Vite localhost). Set to
    your Netlify origin(s) in production. Use `*` only if you intentionally want open CORS.
  - In-process rate limit (`RATE_LIMIT_PER_MIN`, default 600) on `/api/*` except health
  - Map listing requires a bounded bbox (`MAX_BBOX_SPAN_DEG`, default 0.5°)
  - `BPF_ENV=production` disables `/docs`, `/redoc`, and `/openapi.json`
- Prefer binding uvicorn to `127.0.0.1` behind a reverse proxy / tunnel
