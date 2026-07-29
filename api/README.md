# API

## Supported runtime (Python)

```bash
cd api
python -m pip install -r requirements.txt
python -m py.ingest    # once, after CSVs are in ../data/
python -m py.server    # http://127.0.0.1:8080
```

Routes: `/api/health`, `/api/meta`, `/api/meters`, `/api/meters/{meter_no}`.

## Optional reference (Rust)

Sources under `src/` mirror the Python behaviour (Axum + rusqlite). Use when your
Rust toolchain can build; on some Windows setups Defender blocks cargo builds.

```bash
cargo run --bin ingest
cargo run
```

Generated: `parking.db`, `.cache/` (both gitignored).
