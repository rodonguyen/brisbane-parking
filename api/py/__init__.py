"""
Brisbane Parking API (Python runtime).

Mirrors the Rust Axum API in this folder: same routes, SQLite schema,
24h cache, and next-hour / analog insight logic. Use this when Rust
cannot compile (e.g. Windows Defender blocking cargo build scripts).

  python -m ingest
  python -m server
"""
