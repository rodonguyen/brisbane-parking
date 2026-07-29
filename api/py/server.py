from __future__ import annotations

import sys
from pathlib import Path

ROOT_API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_API))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from py.cache import InsightCache
from py.db import connect
from py.insight import InsightEngine

DB_PATH = ROOT_API / "parking.db"
CACHE_DIR = ROOT_API / ".cache"

if not DB_PATH.exists():
    raise SystemExit(
        f"Database not found at {DB_PATH}. Run: python -m py.ingest (from api/)"
    )

conn = connect(DB_PATH)
cache = InsightCache(CACHE_DIR)
engine = InsightEngine(conn, cache)

app = FastAPI(title="Brisbane Parking API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "brisbane-parking-api"}


@app.get("/api/meta")
def meta():
    return engine.meta()


@app.get("/api/meters")
def list_meters(
    west: float | None = Query(None),
    south: float | None = Query(None),
    east: float | None = Query(None),
    north: float | None = Query(None),
    suburb: str | None = Query(None),
    limit: int = Query(250, ge=1, le=400),
):
    return engine.map_meters(
        west=west,
        south=south,
        east=east,
        north=north,
        suburb=suburb,
        limit=limit,
    )


@app.get("/api/meters/{meter_no}")
def meter_detail(meter_no: str):
    insight = engine.meter_insight(meter_no)
    if insight is None:
        raise HTTPException(status_code=404, detail="meter not found")
    return insight


def main() -> None:
    import uvicorn

    uvicorn.run("py.server:app", host="127.0.0.1", port=8080, reload=False)


if __name__ == "__main__":
    main()
