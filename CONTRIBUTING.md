# Contributing

Thanks for helping improve Brisbane Parking Finder.

## Setup

1. Place BCC CSVs under `data/` (see `data/README.md`).
2. Ingest once: `make ingest` (or `cd api && python -m py.ingest`).
3. Run API + web: `make dev` (or start `python -m py.server` in `api/` and `npm run dev` in `web/`).

Python FastAPI (`api/py/`) is the supported runtime. Rust under `api/src/` is an optional reference implementation — keep parity when changing API behaviour if you touch both.

## Guidelines

- Prefer small, focused PRs with a short description of *why*
- Do not commit CSVs, `api/parking.db`, `api/.cache/`, `node_modules/`, or `__pycache__/`
- Preserve existing routes: `/api/health`, `/api/meta`, `/api/meters` (viewport bbox), `/api/meters/{meter_no}`
- Match existing style in the file you edit; no drive-by refactors
- For UI changes, keep the map-first civic utility tone (see `.agents/skills/design-taste-frontend` if present)

## Checks

```bash
cd web && npm run lint && npm run build
# API: smoke-test after ingest
curl -s http://127.0.0.1:8080/api/health
curl -s http://127.0.0.1:8080/api/meta | head
```

## Licence

Code contributions are under MIT. Dataset attribution remains CC BY 4.0 to
Brisbane City Council (see `NOTICE`).
