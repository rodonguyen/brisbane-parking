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
- Frontend auth (Clerk) is optional for browsing; the public API remains unauthenticated unless you add your own hardening before exposing it
- Treat the API as a local/dev service unless you add rate limits, auth, or network controls for production