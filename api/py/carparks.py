"""Off-street car parks for the map (data/carparks/carparks.json).

The dataset is built offline (see data/carparks/README.md). Here we load it once and
shape each record into what a driver needs: name, address, hours, height, prices
grouped into readable rows, and a link only when the page is for that one car park.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "carparks" / "carparks.json"

GROUPS = [
    ("casual", "Casual"),
    ("early_bird", "Early bird"),
    ("night", "Night"),
    ("weekend", "Weekend"),
    ("flat", "Flat rate"),
    ("other", "Other"),
]
_GROUP_TITLE = dict(GROUPS)


def _money(v: float | None) -> str | None:
    if v is None:
        return None
    if float(v) == 0:
        return "Free"
    return f"${float(v):.2f}".replace(".00", "")


def _dur(h: float) -> str:
    if h < 1:
        return f"{round(h * 60)} min"
    n = f"{h:.2f}".rstrip("0").rstrip(".")
    return f"{n} hr" if h == 1 else f"{n} hrs"


def _tidy(label: str) -> str:
    out = re.sub(r"^(Casual|Hourly) Parking\s*-\s*", "", label, flags=re.I)
    out = re.sub(r"\s*-\s*Flat Rate( per day)?$", "", out, flags=re.I)
    out = re.sub(r"^(Early Bird|Night|Weekend|Evening) Parking\s*-\s*", "", out, flags=re.I)
    out = re.sub(r"\s+Parking$", "", out, flags=re.I)
    out = re.sub(r"\s+from$", "", out, flags=re.I).strip()
    return out or label


def _band(r: dict) -> str:
    f, t = r.get("duration_hours_from"), r.get("duration_hours_to")
    if r.get("kind") == "daily_max" and not re.search(r"before|leaving|entering", r.get("label") or "", re.I):
        return "Max per day"
    if f is not None and t is not None:
        return f"Up to {_dur(t)}" if f == 0 else f"{_dur(f)} – {_dur(t)}"
    if f is not None:
        return f"{_dur(f)}+"
    return _tidy(r.get("label") or "")


def _hm(w: str) -> str:
    m = re.fullmatch(r"(\d\d:\d\d)-(\d\d:\d\d)", w)
    if m:
        return f"{m.group(1)}–{m.group(2)}"
    if w.startswith("-"):
        return "before " + w[1:]
    if w.endswith("-"):
        return w[:-1] + " or later"
    return w


def _when(r: dict) -> str | None:
    parts = [r.get("days")]
    if r.get("entry_window"):
        parts.append("enter " + _hm(r["entry_window"]))
    if r.get("exit_window"):
        parts.append("exit " + _hm(r["exit_window"]))
    s = ", ".join(p for p in parts if p)
    return s or None


def rate_groups(rates: list[dict]) -> list[dict]:
    """Group raw rate rows into titled lists of {label, price, online_price, when}."""
    by: dict[str, list[dict]] = {}
    for r in rates:
        label = r.get("label") or ""
        if re.search(r"lost ticket", label, re.I):
            continue
        kind = r.get("kind") or "other"
        group = "casual" if kind in ("hourly", "daily_max") else (kind if kind in _GROUP_TITLE else "other")
        price, online = _money(r.get("price_aud")), _money(r.get("online_price_aud"))
        if price is None and online is None:
            continue
        title = _GROUP_TITLE[group]
        tidy = _tidy(label)
        # Duration-style labels ("0- 2 Hours") read better rebuilt; named ones ("Overnight & Hotel") stay.
        if group == "casual" or (r.get("duration_hours_from") is not None and re.match(r"^(up to\s*)?\d", tidy, re.I)):
            lab = _band(r)
        else:
            lab = tidy
        when = _when(r) if (r.get("entry_window") or r.get("exit_window") or group != "casual") else None
        low = re.sub(r"^flexible\s+", "", lab.lower())
        if low in (title.lower(), f"{title.lower()} rate", f"{title.lower()} flat rate"):
            lab = ""
        if price and lab.lower() == price.lower():
            lab = "All day"
        if not lab and not when:
            lab = "Flat rate"
        by.setdefault(group, []).append({
            "label": lab or None,
            "price": price,
            "online_price": online if online != price else None,
            "when": when,
        })
    return [{"title": t, "rows": by[g]} for g, t in GROUPS if g in by]


def simplify_hours(h: str | None) -> str | None:
    if not h:
        return None
    if h.startswith("24/7") or (re.search(r"24 hours", h, re.I) and not re.search(r"\d{1,2}:\d{2}", h)):
        return "Open 24/7"
    h = re.sub(r";\s*Monthly subscribers 24 hours", "", h, flags=re.I)
    m = re.fullmatch(r"Mon-Sun: (.+?); Public Holidays: (.+)", h)
    if m and m.group(1) == m.group(2):
        return "Daily " + m.group(1)
    return re.sub(r"^Mon-Sun: ", "Daily ", h)


def _specific_url(url: str | None, counts: Counter) -> str | None:
    if not url or not re.match(r"https?://", url):
        return None
    if counts[url] > 1 or re.search(r"\.(kml|json)(\?|$)|wp-json", url):
        return None
    return url


def shape(records: list[dict]) -> list[dict]:
    counts = Counter(r.get("url") for r in records if r.get("url"))
    out = []
    for r in records:
        if r.get("lat") is None or r.get("lng") is None:
            continue
        address = re.sub(r",\s*Australia$", "", r.get("address") or "") or None
        operator = r.get("operator") if r.get("operator") and r.get("operator") != r.get("name") else None
        groups = rate_groups(r.get("rates") or [])
        out.append({
            "id": r["id"],
            "name": r.get("name") or "Car park",
            "address": address,
            "operator": operator,
            "lat": r["lat"],
            "lng": r["lng"],
            "hours": simplify_hours(r.get("hours")),
            "height_m": r.get("height_m"),
            "url": _specific_url(r.get("url"), counts),
            "priced": bool(groups),
            "rates": groups,
        })
    return out


class Carparks:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(os.environ.get("CARPARKS_PATH") or path or DEFAULT_PATH)
        self.items: list[dict] = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = shape(data["carparks"] if isinstance(data, dict) else data)

    def in_bbox(self, west: float, south: float, east: float, north: float) -> list[dict]:
        return [c for c in self.items if west <= c["lng"] <= east and south <= c["lat"] <= north]
