from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path

from .timectx import day_class, season

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS meters (
    meter_no TEXT PRIMARY KEY,
    category TEXT,
    street TEXT,
    suburb TEXT,
    max_stay_hrs TEXT,
    restrictions TEXT,
    operational_day TEXT,
    operational_time TEXT,
    tar_zone TEXT,
    tar_rate_weekday TEXT,
    tar_rate_ah_we TEXT,
    loc_desc TEXT,
    veh_bays INTEGER,
    mc_bays INTEGER,
    longitude REAL,
    latitude REAL,
    mobile_zone TEXT,
    max_cap_chg TEXT
);

CREATE TABLE IF NOT EXISTS occupancy (
    mobile_zone TEXT NOT NULL,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    occupancy_pred REAL NOT NULL,
    day_class TEXT NOT NULL,
    season TEXT NOT NULL,
    PRIMARY KEY (mobile_zone, date, hour)
);

CREATE INDEX IF NOT EXISTS idx_occ_zone_hour_ctx
    ON occupancy (mobile_zone, hour, day_class, season);
CREATE INDEX IF NOT EXISTS idx_occ_zone_date
    ON occupancy (mobile_zone, date);
CREATE INDEX IF NOT EXISTS idx_meters_zone ON meters (mobile_zone);
CREATE INDEX IF NOT EXISTS idx_meters_geo ON meters (latitude, longitude);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def clear_data(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM occupancy")
    conn.execute("DELETE FROM meters")
    conn.commit()


def _strip_bom(s: str) -> str:
    return s.lstrip("\ufeff").strip()


def ingest_meters(conn: sqlite3.Connection, csv_path: Path) -> int:
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            try:
                lon = float(row.get("LONGITUDE") or 0)
                lat = float(row.get("LATITUDE") or 0)
            except ValueError:
                continue
            if not lon or not lat:
                continue
            veh = row.get("VEH_BAYS_INT") or row.get("VEH_BAYS") or "0"
            try:
                veh_bays = int(float(veh))
            except ValueError:
                veh_bays = 0
            try:
                mc_bays = int(float(row.get("MC_BAYS") or 0))
            except ValueError:
                mc_bays = 0
            rows.append(
                (
                    _strip_bom(row.get("METER_NO", "")),
                    row.get("CATEGORY", ""),
                    row.get("STREET", ""),
                    row.get("SUBURB", ""),
                    row.get("MAX_STAY_HRS", ""),
                    row.get("RESTRICTIONS", ""),
                    row.get("OPERATIONAL_DAY", ""),
                    row.get("OPERATIONAL_TIME", ""),
                    row.get("TAR_ZONE", ""),
                    row.get("TAR_RATE_WEEKDAY", ""),
                    row.get("TAR_RATE_AH_WE", ""),
                    row.get("LOC_DESC", ""),
                    veh_bays,
                    mc_bays,
                    lon,
                    lat,
                    row.get("MOBILE_ZONE", ""),
                    row.get("MAX_CAP_CHG", ""),
                )
            )
    conn.executemany(
        """INSERT OR REPLACE INTO meters (
            meter_no, category, street, suburb, max_stay_hrs, restrictions,
            operational_day, operational_time, tar_zone, tar_rate_weekday,
            tar_rate_ah_we, loc_desc, veh_bays, mc_bays, longitude, latitude,
            mobile_zone, max_cap_chg
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    return len(rows)


def ingest_occupancy(conn: sqlite3.Connection, csv_path: Path) -> int:
    count = 0
    batch: list[tuple] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zone = _strip_bom(row["MOBILE_ZONE"])
            d = row["DATE"]
            hour = int(float(row["HOUR"]))
            pred = float(row["OCCUPANCY_PRED"])
            parsed = date.fromisoformat(d)
            batch.append((zone, d, hour, pred, day_class(parsed), season(parsed)))
            count += 1
            if len(batch) >= 20_000:
                conn.executemany(
                    """INSERT OR IGNORE INTO occupancy
                       (mobile_zone, date, hour, occupancy_pred, day_class, season)
                       VALUES (?,?,?,?,?,?)""",
                    batch,
                )
                conn.commit()
                batch.clear()
                if count % 500_000 == 0:
                    print(f"  … {count} rows from {csv_path.name}")
        if batch:
            conn.executemany(
                """INSERT OR IGNORE INTO occupancy
                   (mobile_zone, date, hour, occupancy_pred, day_class, season)
                   VALUES (?,?,?,?,?,?)""",
                batch,
            )
            conn.commit()
    return count
