#!/usr/bin/env python3
"""Geocode car parks whose source pages publish no coordinates.

Uses OpenStreetMap Nominatim (https://nominatim.org/release-docs/latest/api/Search/)
within its usage policy: <= 1 request/second, identifying User-Agent, results cached
in geocode_cache.json so each query is sent only once. Results © OpenStreetMap
contributors, ODbL.

Targets:
  other_operators.json  Cornerstone records (lat/lng written back, note appended)
  malls.json            all records (NOT written back - malls.json stays as scraped;
                        merge_carparks.py reads coordinates from the cache)

Every hit must fall inside the Greater Brisbane bbox (lat -27.75..-27.0, lng 152.65..153.35).
"""
import json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, ".."))
CACHE = os.path.join(BASE, "geocode_cache.json")
UA = "brisbane-parking-finder-data-build/0.1 (one-off batch geocode of ~100 car-park addresses)"
VIEWBOX = "152.65,-27.0,153.35,-27.75"
_last = [0.0]


def in_bbox(lat, lng):
    return -27.75 <= lat <= -27.0 and 152.65 <= lng <= 153.35


def load_cache():
    return json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def nominatim(q, cache):
    if q in cache:
        return cache[q]
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "au", "viewbox": VIEWBOX, "bounded": 1, "addressdetails": 0})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-AU"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)
    _last[0] = time.time()
    hit = None
    if res:
        x = res[0]
        hit = {"lat": float(x["lat"]), "lng": float(x["lon"]), "display_name": x["display_name"],
               "category": x.get("category"), "type": x.get("type"), "addresstype": x.get("addresstype")}
    cache[q] = hit
    print(("OK  " if hit else "MISS"), q, "->", hit and hit["display_name"][:90], flush=True)
    return hit


def clean_addr(a):
    a = re.sub(r'\([^)]*\)', '', a or '')
    a = a.replace('’', "'").replace('–', '-')
    a = re.sub(r'\bQ\b(?=\s*\d{4})', 'QLD', a)
    a = re.sub(r',?\s*Australia$', '', a).strip(' ,')
    if not re.search(r'\bQLD\b|Queensland', a, re.I):
        a += ', QLD'
    return a


def strip_number(a):
    return re.sub(r'^\s*\d+[A-Za-z]?(?:-\d+)?\s+', '', a)


def precision(hit):
    """'street' when Nominatim only matched a road; otherwise the matched feature (house/building/POI)."""
    if hit["category"] == "highway" or hit.get("addresstype") == "road":
        return "street"
    if hit["category"] == "place" and hit["type"] == "house":
        return "address"
    return "building_or_poi"


def geocode(queries, cache):
    """Try each query in order; return (hit, query) for the first in-bbox hit."""
    for q in queries:
        hit = nominatim(q, cache)
        if hit and in_bbox(hit["lat"], hit["lng"]):
            return hit, q
    return None, None


# Extra queries for addresses Nominatim can't parse as published.
OVERRIDES = {
    "cornerstone-240-st-pauls-terrace": ["240 Saint Pauls Terrace, Fortitude Valley QLD", "Saint Pauls Terrace, Fortitude Valley QLD"],
    "cornerstone-4-walden-lane": ["Walden Lane, Bowen Hills QLD", "Walden Lane, Herston QLD"],
    "cornerstone-9-browning-street": ["9 Browning Street, South Brisbane QLD", "Browning Street, West End QLD", "Browning Street, South Brisbane QLD"],
    "dfo-brisbane": ["DFO Brisbane", "18th Avenue, Brisbane Airport QLD"],
    "myer-centre": ["Uptown, Queen Street, Brisbane City QLD", "Myer Centre, Brisbane City QLD", "Elizabeth Street, Brisbane City QLD 4000"],
    "riverlink": ["Riverlink Shopping Centre, North Ipswich", "The Terrace, North Ipswich QLD"],
}


def cornerstone_queries(r):
    a = clean_addr(r["address"])
    qs = [a, f"{r['name']}, {a}"]
    if strip_number(a) != a:
        qs.append(strip_number(a))
    return qs + OVERRIDES.get(r["id"], [])


def mall_queries(r):
    qs = []
    if r.get("address"):
        a = clean_addr(r["address"])
        qs += [f"{r['name']}, {a}", a]
    qs.append(f"{r['name']}, QLD")
    return qs + OVERRIDES.get(r["id"], [])


def main():
    cache = load_cache()
    try:
        oo_path = os.path.join(BASE, "other_operators.json")
        oo = json.load(open(oo_path))
        miss = []
        for r in oo:
            if r["source"] != "cornerstone":
                continue
            # recompute from cache each run (drop any earlier geocode note)
            r["notes"] = " || ".join(n for n in (r["notes"] or "").split(" || ") if n and "geocoded via" not in n) or None
            r["lat"] = r["lng"] = None
            hit, q = geocode(cornerstone_queries(r), cache)
            if not hit:
                miss.append(r["id"]); continue
            r["lat"], r["lng"] = round(hit["lat"], 7), round(hit["lng"], 7)
            note = (f"lat/lng geocoded via OSM Nominatim from '{q}' (precision: {precision(hit)}; "
                    f"matched {hit['category']}/{hit['type']}); not published by operator")
            r["notes"] = (r["notes"] + " || " + note) if r["notes"] else note
        json.dump(oo, open(oo_path, "w"), indent=2, ensure_ascii=False)
        print("cornerstone misses:", miss)

        malls = json.load(open(os.path.join(BASE, "malls.json")))
        mmiss = []
        for r in malls:
            hit, q = geocode(mall_queries(r), cache)
            if not hit:
                mmiss.append(r["id"])
        print("mall misses:", mmiss)
    finally:
        json.dump(cache, open(CACHE, "w"), indent=1, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
