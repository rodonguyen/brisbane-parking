#!/usr/bin/env python3
"""Normalise raw Overpass output to data/carparks/osm.json. No invented values: null when tag absent."""
import json, re, datetime, pathlib

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE / "overpass_greater_brisbane.json"
OUT = HERE.parent.parent / "osm.json"

raw = json.loads(RAW.read_text())
checked = raw.get("osm3s", {}).get("timestamp_osm_base")
fetched = datetime.datetime.fromtimestamp(RAW.stat().st_mtime, datetime.timezone.utc).isoformat(timespec="seconds")

def num(v):
    if v is None:
        return None
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(m)?\s*", v)
    if not m:
        return None
    f = float(m.group(1))
    return int(f) if f.is_integer() else f

def address(t):
    parts = {k[5:]: v for k, v in t.items() if k.startswith("addr:")}
    if not parts:
        return None
    street = " ".join(x for x in [parts.get("housenumber"), parts.get("street")] if x)
    line = ", ".join(x for x in [street or parts.get("place"), parts.get("suburb") or parts.get("city"), " ".join(x for x in [parts.get("state"), parts.get("postcode")] if x)] if x)
    return line or None

FEATURE_KEYS = re.compile(r"^(capacity:.+|park_ride|maxstay.*|supervised|covered|lit|surface|charge:.+|fee:.+|payment:.+|parking:.+|motorcar|motorcycle|hgv|wheelchair|toilets|levels|building:levels)$")

out = []
for e in raw["elements"]:
    t = e.get("tags", {})
    lat = e.get("lat") if e["type"] == "node" else e.get("center", {}).get("lat")
    lng = e.get("lon") if e["type"] == "node" else e.get("center", {}).get("lon")
    fee = t.get("fee")
    fee_n = "yes" if fee == "yes" else "no" if fee == "no" else None
    notes = []
    if fee and fee not in ("yes", "no"):
        notes.append(f"raw fee tag: {fee}")
    if t.get("maxheight") and num(t.get("maxheight")) is None:
        notes.append(f"raw maxheight tag: {t['maxheight']}")
    if t.get("capacity") and num(t.get("capacity")) is None:
        notes.append(f"raw capacity tag: {t['capacity']}")
    for k in ("description", "note"):
        if t.get(k):
            notes.append(f"{k}: {t[k]}")
    cap = num(t.get("capacity"))
    out.append({
        "id": f"osm:{e['type']}/{e['id']}",
        "source": "osm",
        "operator": t.get("operator"),
        "name": t.get("name"),
        "address": address(t),
        "lat": lat,
        "lng": lng,
        "url": t.get("website") or t.get("contact:website") or t.get("url"),
        "checked_at": checked,
        "hours": t.get("opening_hours"),
        "fee": fee_n,
        "charge": t.get("charge"),
        "height_m": num(t.get("maxheight")),
        "capacity": int(cap) if isinstance(cap, (int, float)) else None,
        "parking_type": t.get("parking"),
        "access": t.get("access"),
        "features": {k: v for k, v in t.items() if FEATURE_KEYS.match(k)},
        "rates": [],
        "discounts": [],
        "notes": "; ".join(notes) or None,
    })

meta = {
    "source": "OpenStreetMap via Overpass (overpass.kumi.systems)",
    "licence": "ODbL 1.0 — © OpenStreetMap contributors",
    "bbox": [-27.75, 152.65, -27.0, 153.35],
    "query": 'amenity=parking AND (parking in multi-storey|underground|surface|rooftop OR fee present OR name present); out center tags',
    "osm_base_timestamp": checked,
    "fetched_at": fetched,
    "count": len(out),
}
OUT.write_text(json.dumps({"meta": meta, "carparks": out}, indent=1, ensure_ascii=False))
print(OUT, len(out))
