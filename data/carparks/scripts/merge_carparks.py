#!/usr/bin/env python3
"""Merge the per-source car-park files into one de-duplicated carparks.json.

Inputs (all in data/carparks/):
  secure.json, wilson.json, other_operators.json   operator pages (highest precedence)
  council_and_public.json                           council, park 'n' ride, hospitals, unis, airport
  malls.json                                        shopping-centre pages (no published coords;
                                                    lat/lng filled from geocode_cache.json)
osm.json is NOT merged: it has no rates and ~5.8k mostly-private car parks; keep it as a map layer.

Duplicates are linked only via the reviewed SAME_AS table below. Each run also prints
"unreviewed candidates" (shared street address, or <=150 m apart with similar names, or
<=40 m apart) that are in neither SAME_AS nor NOT_SAME, so new overlaps get a human look.

The merged record is the higher-precedence one; empty fields (coords, hours, height,
capacity, address, rates) are filled from its duplicates, features/discounts are unioned,
and every absorbed record is listed in `also_listed_in`.

Output: carparks.json  {"meta": {...}, "carparks": [...]}
"""
import datetime, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import geocode  # noqa: E402  (query builders + bbox; cache lookups only, no network)

SOURCES = [  # (file, list key or None, precedence: lower wins)
    ("secure.json", None, 0),
    ("wilson.json", None, 0),
    ("other_operators.json", None, 0),
    ("council_and_public.json", "carparks", 1),
    ("malls.json", None, 2),
]

# Reviewed 2026-10-25. (primary id, duplicate id)
SAME_AS = [
    ("secure:15063c61-02e4-4e74-a17c-af090083ebf6", "emporium"),
    ("secure:d2db06af-a10e-44ee-bf10-af08004db85f", "macarthur-central"),
    ("secure:a18722b1-0865-4a1b-a72a-aef400856a59", "mcwhirters"),
    ("secure:c7672c74-0eb1-47cf-bb12-aed8007f30b8", "southpoint-south-bank"),
    ("secure:3f3d3434-2fb1-4622-8134-aed100a633d7", "wintergarden"),
    ("wilson-4084", "hosp:rbwh-herston-rd"),
    ("wilson-4347", "hosp:rbwh-butterfield"),
    ("wilson-4349", "hosp:rbwh-northern-p2"),
    ("wilson-4350", "hosp:pah-wilson"),
    ("firstparking-pa-central", "hosp:pah-first"),
    ("firstparking-valley-metro", "valley-metro"),
    ("cornerstone-butterfield-street-car-park-rbwh", "hosp:rbwh-royal-brisbane-cornerstone"),
    ("cornerstone-coorparoo-square", "coorparoo-square"),
    ("nationwide-toowong-village-and-tower", "toowong-village"),
]
# Reviewed candidates that are different car parks (neighbours / same street, different number).
NOT_SAME = {frozenset(p) for p in [
    ("secure:b80afecc-84b2-4bca-be71-aef600b176ab", "cornerstone-9-browning-street"),
    ("secure:b8035478-5ba1-48c9-bed9-aed70085f6ae", "wilson-4170"),
    ("secure:991e6b55-ecef-4356-a65d-b2ac006184ba", "cornerstone-butterfield-street-car-park-rbwh"),
    ("secure:9196cd4d-779a-47c5-aa51-b416001a0429", "mcwhirters"),
    ("secure:432b760b-5bbf-43e3-9c47-aed80087b075", "wilson-4256"),
    ("secure:432b760b-5bbf-43e3-9c47-aed80087b075", "southpoint-south-bank"),
    ("wilson-4165", "cornerstone-313-adelaide-street"),
    ("wilson-4095", "cornerstone-313-adelaide-street"),
    ("wilson-4365", "cornerstone-100-edward-street"),
    ("wilson-4121", "bcc:king-george-square"),
    ("cornerstone-parkthe-fort", "mcwhirters"),
    ("nationwide-toowong-village-and-tower", "translink-pnr:toowong-station"),
    ("translink-pnr:toowong-station", "toowong-village"),
]}

CORE = ["id", "source", "operator", "name", "address", "lat", "lng", "coord_source", "coord_precision", "url",
        "checked_at", "hours", "height_m", "capacity", "features", "rates", "discounts", "notes"]
KIND_MAP = {"max_daily": "daily_max", "evening": "night", "public_holiday": "flat", "day_pass": "flat",
            "motorcycle": "other", "fee": "other", "multi_day": "other", "monthly": "other"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def hav(a, b):
    R = 6371000
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lng"] - a["lng"])
    return 2 * R * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


ABBR = {'street': 'st', 'st': 'st', 'road': 'rd', 'rd': 'rd', 'terrace': 'tce', 'tce': 'tce', 'avenue': 'ave', 'ave': 'ave',
        'drive': 'dr', 'dr': 'dr', 'lane': 'ln', 'ln': 'ln', 'place': 'pl', 'pl': 'pl', 'parade': 'pde', 'boulevard': 'blvd',
        'crescent': 'cres', 'court': 'ct', 'highway': 'hwy'}


def addr_keys(a):
    a = (a or '').lower().replace('’', "'").replace('saint', 'st')
    return {(m.group(1), m.group(2).replace("'", '').strip(), ABBR[m.group(3)]) for m in re.finditer(
        r"\b(\d+)[a-z]?(?:\s*-\s*\d+)?\s+([a-z' ]+?)\s+(street|st|road|rd|terrace|tce|avenue|ave|drive|dr|lane|ln|place|pl|"
        r"parade|boulevard|crescent|court|highway)\b", a)}


STOP = set('car park parking the of and centre center shopping brisbane qld st street road village plaza cnr secure wilson'.split())


def toks(n):
    return set(re.findall(r'[a-z0-9]+', (n or '').lower())) - STOP


def hours_str(h):
    if not isinstance(h, dict):
        return h
    days = [h.get(d) for d in DAYS]
    parts = [f"Mon-Sun: {days[0]}"] if len(set(days)) == 1 and days[0] else [f"{d[:3]}: {h[d]}" for d in DAYS if h.get(d)]
    parts += [f"{k}: {v}" for k, v in h.items() if k not in DAYS]
    return "; ".join(parts) or None


def normalise(r, fname, prec, cache):
    extra = {k: v for k, v in r.items() if k not in CORE}
    feats = r.get("features")
    if isinstance(feats, dict):
        extra["feature_details"] = feats
        feats = sorted(feats)
    out = {k: r.get(k) for k in CORE}
    out["features"] = list(feats or [])
    out["hours"] = hours_str(r.get("hours"))
    out["coord_source"] = "source" if r.get("lat") is not None else None
    if "geocoded via OSM Nominatim" in (r.get("notes") or ""):
        out["coord_source"] = "geocoded"
        m = re.search(r"precision: (\w+)", r["notes"])
        out["coord_precision"] = m.group(1) if m else None
    if out["lat"] is None and fname == "malls.json":
        for q in geocode.mall_queries(r):
            hit = cache.get(q)
            if hit and geocode.in_bbox(hit["lat"], hit["lng"]):
                out["lat"], out["lng"] = round(hit["lat"], 7), round(hit["lng"], 7)
                out["coord_source"], out["coord_precision"] = "geocoded", geocode.precision(hit)
                extra["geocode_query"] = q
                break
    rates = []
    for x in r.get("rates") or []:
        x = dict(x)
        if x.get("kind") in KIND_MAP:
            x["source_kind"] = x["kind"]
            x["kind"] = KIND_MAP[x["kind"]]
        rates.append(x)
    out["rates"] = rates
    out["discounts"] = [x if isinstance(x, dict) else {"label": str(x), "details": None} for x in r.get("discounts") or []]
    out["source_file"] = fname
    out["also_listed_in"] = []
    out["extra"] = extra
    out["_prec"] = prec
    return out


def candidates(recs):
    for i, a in enumerate(recs):
        for b in recs[i + 1:]:
            if a["source_file"] == b["source_file"]:
                continue
            shared = bool(addr_keys(a["address"]) & addr_keys(b["address"]))
            d = hav(a, b) if a["lat"] is not None and b["lat"] is not None else None
            ta, tb = toks(a["name"]), toks(b["name"])
            j = len(ta & tb) / max(1, min(len(ta), len(tb))) if ta and tb else 0
            if shared or (d is not None and d < 150 and j >= 0.5) or (d is not None and d < 40):
                yield a["id"], b["id"], d


def absorb(p, d):
    for k in ("address", "lat", "lng", "coord_source", "coord_precision", "hours", "height_m", "capacity", "url"):
        if p.get(k) in (None, "") and d.get(k) not in (None, ""):
            if k in ("lat", "lng", "coord_source", "coord_precision") and p.get("lat") is not None:
                continue
            p[k] = d[k]
    if not p["rates"] and d["rates"]:
        p["rates"] = d["rates"]
        p["extra"]["rates_from"] = d["id"]
    p["features"] = sorted(set(p["features"]) | set(d["features"]))
    labels = {x.get("label") for x in p["discounts"]}
    p["discounts"] += [x for x in d["discounts"] if x.get("label") not in labels]
    p["also_listed_in"].append({"id": d["id"], "source": d["source"], "source_file": d["source_file"],
                                "name": d["name"], "url": d["url"], "rates_count": len(d["rates"])})


def main():
    cache = json.load(open(os.path.join(BASE, "geocode_cache.json")))
    recs = []
    for fname, key, prec in SOURCES:
        data = json.load(open(os.path.join(BASE, fname)))
        recs += [normalise(r, fname, prec, cache) for r in (data[key] if key else data)]
    by_id = {r["id"]: r for r in recs}
    assert len(by_id) == len(recs), "duplicate ids across sources"

    same = {frozenset(p) for p in SAME_AS}
    unreviewed = [(a, b, d) for a, b, d in candidates(recs) if frozenset((a, b)) not in same | NOT_SAME]
    for a, b, d in unreviewed:
        print(f"UNREVIEWED candidate: {a} <-> {b} ({'?' if d is None else round(d)} m)", file=sys.stderr)

    dropped = set()
    for pid, did in SAME_AS:
        p, d = by_id[pid], by_id[did]
        if d["_prec"] < p["_prec"]:
            p, d = d, p
        absorb(p, d)
        dropped.add(d["id"])
    out = [r for r in recs if r["id"] not in dropped]
    for r in out:
        r.pop("_prec")
    meta = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "bbox": {"lat": [-27.75, -27.0], "lng": [152.65, 153.35]},
        "inputs": {f: sum(1 for r in recs if r["source_file"] == f) for f, _, _ in SOURCES},
        "duplicates_merged": len(dropped),
        "count": len(out),
        "with_rates": sum(1 for r in out if r["rates"]),
        "with_coords": sum(1 for r in out if r["lat"] is not None),
        "geocoded": sum(1 for r in out if r["coord_source"] == "geocoded"),
        "unreviewed_candidates": len(unreviewed),
        "notes": ("Rates/hours are transcribed from each operator's public page at checked_at; check signage. "
                  "coord_source 'geocoded' = OSM Nominatim (© OpenStreetMap contributors, ODbL) from the published "
                  "address; coord_precision 'street' means only the street was matched. osm.json is a separate layer."),
    }
    json.dump({"meta": meta, "carparks": out}, open(os.path.join(BASE, "carparks.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
