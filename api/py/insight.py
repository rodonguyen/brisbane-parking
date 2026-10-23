from __future__ import annotations

import math
import sqlite3
from typing import Any

from .cache import InsightCache
from .hours import evaluate_parkability
from .timectx import brisbane_clock, chance_free, chance_label


def _meter_from_row(row: sqlite3.Row) -> dict[str, Any]:
    keys = set(row.keys())
    return {
        "meter_no": row["meter_no"],
        "street": row["street"],
        "suburb": row["suburb"],
        "loc_desc": row["loc_desc"] if "loc_desc" in keys else "",
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "mobile_zone": row["mobile_zone"],
        "veh_bays": row["veh_bays"] if "veh_bays" in keys else 0,
        "max_stay_hrs": row["max_stay_hrs"] if "max_stay_hrs" in keys else "",
        "operational_day": row["operational_day"] if "operational_day" in keys else "",
        "operational_time": row["operational_time"] if "operational_time" in keys else "",
        "restrictions": row["restrictions"] if "restrictions" in keys else "",
        "tar_rate_weekday": row["tar_rate_weekday"] if "tar_rate_weekday" in keys else "",
        "tar_rate_ah_we": row["tar_rate_ah_we"] if "tar_rate_ah_we" in keys else "",
        "category": row["category"] if "category" in keys else "",
        "chance_free": None,
        "occupancy_pred": None,
        "lookup_method": None,
        "parkable": True,
        "park_status": "operating",
        "park_reason": "",
    }


def _apply_parkability(
    meter: dict[str, Any],
    date_str: str,
    hour: int,
    occ: float | None,
    method: str,
) -> None:
    status = evaluate_parkability(
        operational_day=meter.get("operational_day") or "",
        operational_time=meter.get("operational_time") or "",
        restrictions=meter.get("restrictions") or "",
        date_str=date_str,
        hour=hour,
    )
    meter["parkable"] = status.parkable
    meter["park_status"] = status.status
    meter["park_reason"] = status.reason
    meter["lookup_method"] = method
    meter["occupancy_pred"] = occ
    # Chance % only applies during paid operating hours.
    if status.status == "operating" and occ is not None:
        meter["chance_free"] = chance_free(occ)
    else:
        meter["chance_free"] = None


def resolve_occupancy(
    conn: sqlite3.Connection,
    zone: str,
    date_str: str,
    hour: int,
    day_cls: str,
    season_s: str,
) -> tuple[float | None, str]:
    row = conn.execute(
        "SELECT occupancy_pred FROM occupancy WHERE mobile_zone=? AND date=? AND hour=?",
        (zone, date_str, hour),
    ).fetchone()
    if row:
        return float(row[0]), "exact"

    row = conn.execute(
        """SELECT AVG(occupancy_pred), COUNT(*) FROM occupancy
           WHERE mobile_zone=? AND hour=? AND day_class=? AND season=?""",
        (zone, hour, day_cls, season_s),
    ).fetchone()
    if row and row[1] and row[1] > 0:
        return float(row[0]), f"analog:{day_cls}:{season_s}:n={row[1]}"

    row = conn.execute(
        "SELECT AVG(occupancy_pred), COUNT(*) FROM occupancy WHERE mobile_zone=? AND hour=?",
        (zone, hour),
    ).fetchone()
    if row and row[1] and row[1] > 0:
        return float(row[0]), f"zone-hour:n={row[1]}"

    return None, "unavailable"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class InsightEngine:
    def __init__(self, conn: sqlite3.Connection, cache: InsightCache) -> None:
        self.conn = conn
        self.cache = cache

    def meta(self) -> dict[str, Any]:
        now_str, date_str, next_hour, day_cls, season_s, holiday = brisbane_clock()
        key = f"meta:{date_str}:{next_hour}"
        cached = self.cache.get_json(key)
        if cached:
            return cached

        suburbs = [
            r[0]
            for r in self.conn.execute(
                "SELECT DISTINCT suburb FROM meters WHERE suburb IS NOT NULL AND suburb != '' ORDER BY suburb"
            )
        ]
        total = self.conn.execute("SELECT COUNT(*) FROM meters").fetchone()[0]
        resp = {
            "brisbane_now": now_str,
            "next_hour": next_hour,
            "target_date": date_str,
            "day_class": day_cls,
            "season": season_s,
            "is_holiday": holiday,
            "suburbs": suburbs,
            "meter_count": total,
        }
        self.cache.set_json(key, resp)
        return resp

    def map_meters(
        self,
        *,
        west: float | None = None,
        south: float | None = None,
        east: float | None = None,
        north: float | None = None,
        suburb: str | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        now_str, date_str, next_hour, day_cls, season_s, _ = brisbane_clock()
        limit = max(1, min(limit, 1000))

        if any(v is None for v in (west, south, east, north)):
            raise ValueError("bbox (west, south, east, north) is required")

        # Quantize bbox for cache hits while panning slightly
        qw, qs, qe, qn = (
            round(west, 3),  # type: ignore[arg-type]
            round(south, 3),  # type: ignore[arg-type]
            round(east, 3),  # type: ignore[arg-type]
            round(north, 3),  # type: ignore[arg-type]
        )

        sub_key = (suburb or "ALL").upper()
        key = f"map:{date_str}:{next_hour}:{qw}:{qs}:{qe}:{qn}:{sub_key}:{limit}"
        cached = self.cache.get_json(key)
        if cached:
            return cached

        sql = """
            SELECT meter_no, street, suburb, latitude, longitude, mobile_zone,
                   operational_day, operational_time, restrictions
            FROM meters
            WHERE longitude BETWEEN ? AND ? AND latitude BETWEEN ? AND ?
        """
        params: list[Any] = [west, east, south, north]
        if suburb and suburb.upper() != "ALL":
            sql += " AND suburb = ?"
            params.append(suburb)
        sql += " LIMIT ?"
        params.append(limit)

        meters = []
        # Meters share zones (945 meters, 617 zones): resolve each zone once.
        zone_occ: dict[str, tuple[float | None, str]] = {}
        for row in self.conn.execute(sql, params):
            zone = row["mobile_zone"]
            if zone not in zone_occ:
                zone_occ[zone] = resolve_occupancy(
                    self.conn, zone, date_str, next_hour, day_cls, season_s
                )
            occ, method = zone_occ[zone]
            pin = {
                "meter_no": row["meter_no"],
                "street": row["street"],
                "suburb": row["suburb"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "mobile_zone": row["mobile_zone"],
                "operational_day": row["operational_day"],
                "operational_time": row["operational_time"],
                "restrictions": row["restrictions"] or "",
                "chance_free": None,
                "occupancy_pred": occ,
                "lookup_method": method,
                "parkable": True,
                "park_status": "operating",
                "park_reason": "",
            }
            _apply_parkability(pin, date_str, next_hour, occ, method)
            meters.append(pin)

        resp = {
            "brisbane_now": now_str,
            "next_hour": next_hour,
            "target_date": date_str,
            "meters": meters,
            "count": len(meters),
            "limit": limit,
            "truncated": len(meters) >= limit,
        }
        self.cache.set_json(key, resp)
        return resp

    def meter_insight(self, meter_no: str) -> dict[str, Any] | None:
        now_str, date_str, next_hour, day_cls, season_s, holiday = brisbane_clock()
        key = f"insight:{meter_no}:{date_str}:{next_hour}"
        cached = self.cache.get_json(key)
        if cached:
            return cached

        row = self.conn.execute(
            """SELECT meter_no, street, suburb, loc_desc, latitude, longitude, mobile_zone,
                      veh_bays, max_stay_hrs, operational_day, operational_time, restrictions,
                      tar_rate_weekday, tar_rate_ah_we, category
               FROM meters WHERE meter_no=?""",
            (meter_no,),
        ).fetchone()
        if not row:
            return None

        meter = _meter_from_row(row)
        occ, method = resolve_occupancy(
            self.conn, meter["mobile_zone"], date_str, next_hour, day_cls, season_s
        )
        _apply_parkability(meter, date_str, next_hour, occ, method)

        def _series_point(hour: int, occ_pred: float) -> dict[str, Any]:
            st = evaluate_parkability(
                operational_day=meter["operational_day"],
                operational_time=meter["operational_time"],
                restrictions=meter.get("restrictions") or "",
                date_str=date_str,
                hour=hour,
            )
            return {
                "hour": hour,
                "occupancy_pred": occ_pred,
                "chance_free": chance_free(occ_pred),
                "parkable": st.parkable,
                "park_status": st.status,
            }

        today_series = [
            _series_point(int(r[0]), float(r[1]))
            for r in self.conn.execute(
                """SELECT hour, occupancy_pred FROM occupancy
                   WHERE mobile_zone=? AND date=? ORDER BY hour""",
                (meter["mobile_zone"], date_str),
            )
        ]

        typical_series = [
            _series_point(int(r[0]), float(r[1]))
            for r in self.conn.execute(
                """SELECT hour, AVG(occupancy_pred), COUNT(*) FROM occupancy
                   WHERE mobile_zone=? AND day_class=? AND season=?
                   GROUP BY hour ORDER BY hour""",
                (meter["mobile_zone"], day_cls, season_s),
            )
        ]

        context_comparison = []
        for label, dc, s in [
            ("This context", day_cls, season_s),
            ("Weekdays (same season)", "weekday", season_s),
            ("Weekends (same season)", "weekend", season_s),
            ("Holidays (same season)", "holiday", season_s),
        ]:
            r = self.conn.execute(
                """SELECT AVG(occupancy_pred), COUNT(*) FROM occupancy
                   WHERE mobile_zone=? AND hour=? AND day_class=? AND season=?""",
                (meter["mobile_zone"], next_hour, dc, s),
            ).fetchone()
            if r and r[1] and r[1] > 0:
                context_comparison.append(
                    {
                        "label": label,
                        "occupancy_pred": float(r[0]),
                        "chance_free": chance_free(float(r[0])),
                        "sample_count": int(r[1]),
                    }
                )

        nearby = self._nearby(meter, date_str, next_hour, day_cls, season_s)

        if meter["park_status"] == "free":
            park_label = "Free"
        elif not meter["parkable"]:
            park_label = "No parking"
        else:
            park_label = chance_label(meter["chance_free"])

        insight = {
            "meter": meter,
            "brisbane_now": now_str,
            "next_hour": next_hour,
            "target_date": date_str,
            "day_class": day_cls,
            "season": season_s,
            "is_holiday": holiday,
            "next_hour_chance_free": meter["chance_free"],
            "next_hour_occupancy": occ,
            "next_hour_label": park_label,
            "parkable": meter["parkable"],
            "park_status": meter["park_status"],
            "park_reason": meter["park_reason"],
            "lookup_method": method,
            "today_series": today_series,
            "typical_series": typical_series,
            "context_comparison": context_comparison,
            "nearby": nearby,
        }
        self.cache.set_json(key, insight)
        return insight

    def _nearby(
        self,
        meter: dict[str, Any],
        date_str: str,
        hour: int,
        day_cls: str,
        season_s: str,
    ) -> list[dict[str, Any]]:
        lat, lon = meter["latitude"], meter["longitude"]
        d = 0.004
        self_chance = meter.get("chance_free") if meter.get("parkable") else -1.0
        scored: list[dict[str, Any]] = []
        for row in self.conn.execute(
            """SELECT meter_no, street, suburb, latitude, longitude, mobile_zone,
                      operational_day, operational_time, restrictions
               FROM meters
               WHERE meter_no != ?
                 AND latitude BETWEEN ? AND ?
                 AND longitude BETWEEN ? AND ?""",
            (meter["meter_no"], lat - d, lat + d, lon - d, lon + d),
        ):
            dist = haversine_m(lat, lon, row["latitude"], row["longitude"])
            if dist > 300:
                continue
            occ, method = resolve_occupancy(
                self.conn, row["mobile_zone"], date_str, hour, day_cls, season_s
            )
            status = evaluate_parkability(
                operational_day=row["operational_day"] or "",
                operational_time=row["operational_time"] or "",
                restrictions=row["restrictions"] or "",
                date_str=date_str,
                hour=hour,
            )
            if status.status == "restricted":
                continue
            if status.status == "free":
                chance = None
                # Prefer free/off-meter bays when suggesting alternatives.
                sort_chance = 1.0
            else:
                chance = chance_free(occ) if occ is not None else None
                sort_chance = chance if chance is not None else -1.0
            if (
                self_chance is not None
                and status.status == "operating"
                and chance is not None
                and chance <= self_chance
            ):
                continue
            scored.append(
                {
                    "meter_no": row["meter_no"],
                    "street": row["street"],
                    "suburb": row["suburb"],
                    "distance_m": round(dist),
                    "chance_free": chance,
                    "occupancy_pred": occ if status.status == "operating" else None,
                    "parkable": True,
                    "park_status": status.status,
                    "_sort_chance": sort_chance,
                }
            )
        scored.sort(key=lambda x: (-x["_sort_chance"], x["distance_m"]))
        for item in scored:
            item.pop("_sort_chance", None)
        return scored[:3]
