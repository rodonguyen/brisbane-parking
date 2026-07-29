from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))

from py.db import clear_data, connect, ingest_meters, ingest_occupancy, init_schema  # noqa: E402


def find_csv(name: str) -> Path:
    for p in (ROOT / "data" / name, ROOT / name):
        if p.exists():
            return p
    raise FileNotFoundError(name)


def main() -> None:
    db_path = API / "parking.db"
    meters = find_csv("brisbane-parking-meters.csv")
    occ_2026 = find_csv("parking-occupancy-forecasting.csv")
    occ_2025 = find_csv("parking-occupancy-forecasting-2025.csv")

    print(f"DB: {db_path}")
    print(f"Meters: {meters}")
    print(f"Occupancy 2026: {occ_2026}")
    print(f"Occupancy 2025: {occ_2025}")

    conn = connect(db_path)
    init_schema(conn)
    clear_data(conn)

    t0 = time.time()
    n = ingest_meters(conn, meters)
    print(f"Ingested {n} meters in {time.time() - t0:.1f}s")

    t1 = time.time()
    n1 = ingest_occupancy(conn, occ_2026)
    print(f"Ingested {n1} occupancy rows (2026) in {time.time() - t1:.1f}s")

    t2 = time.time()
    n2 = ingest_occupancy(conn, occ_2025)
    print(f"Ingested {n2} occupancy rows (2025) in {time.time() - t2:.1f}s")

    conn.execute("ANALYZE")
    conn.commit()
    conn.close()
    print(f"Done. Total occupancy inserts attempted: {n1 + n2}")


if __name__ == "__main__":
    main()
