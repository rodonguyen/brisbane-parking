# API

## Supported runtime (Python)

```bash
cd api
python -m pip install -r requirements.txt
python -m py.ingest    # once, after CSVs are in ../data/
python -m py.server    # http://127.0.0.1:8080
```

Routes: `/api/health`, `/api/meta`, `/api/meters`, `/api/meters/{meter_no}`, `/api/carparks`, plus the
optional supporter routes `POST /api/support/session`, `GET /api/support/status`,
`POST /api/support/webhook`.

Optional env (see repo root `.env.example`): `CORS_ORIGINS`, `RATE_LIMIT_PER_MIN`,
`MAX_BBOX_SPAN_DEG`, `BPF_ENV=production` (disables OpenAPI docs). `/api/meters`
requires a bounded `west/south/east/north` bbox.

Supporter payments stay off until `STRIPE_SECRET_KEY` is set, and the routes answer
503 until then (see `DEPLOY.md`). Records go to `supporters.db`, never `parking.db`.
Run the tests with `python -m unittest discover -s py -t .` from `api/`.

## Optional reference (Rust)

Sources under `src/` mirror the Python behaviour (Axum + rusqlite). Use when your
Rust toolchain can build; on some Windows setups Defender blocks cargo builds.

```bash
cargo run --bin ingest
cargo run
```

Generated: `parking.db`, `.cache/` (both gitignored).
