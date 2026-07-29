# API

## Supported runtime (Python)

```bash
cd api
python -m pip install -r requirements.txt
python -m py.ingest    # once, after CSVs are in ../data/
python -m py.server    # http://127.0.0.1:8080
```

Routes: `/api/health`, `/api/meta`, `/api/meters`, `/api/meters/{meter_no}`.

Optional env (see repo root `.env.example`): `CORS_ORIGINS`, `RATE_LIMIT_PER_MIN`,
`MAX_BBOX_SPAN_DEG`, `BPF_ENV=production` (disables OpenAPI docs). `/api/meters`
requires a bounded `west/south/east/north` bbox.

## Optional reference (Rust)

Sources under `src/` mirror the Python behaviour (Axum + rusqlite). Use when your
Rust toolchain can build; on some Windows setups Defender blocks cargo builds.

```bash
cargo run --bin ingest
cargo run
```

Generated: `parking.db`, `.cache/` (both gitignored).
