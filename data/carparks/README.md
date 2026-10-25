# Off-street car parks (Greater Brisbane)

Off-street car park data scraped from public operator, council and centre pages, normalised to one schema. Bounding box: lat −27.75..−27.0, lng 152.65..153.35.

## Use this

**`carparks.json`** holds the merged, de-duplicated set: `{"meta": {...}, "carparks": [...]}`. As of 2026-10-25 it has 434 car parks, 220 with priced rates and 413 with coordinates.

Each record has these fields:
- `id`, `source`, `operator`, `name`, `address`
- `lat`, `lng`
- `coord_source` and `coord_precision`:
  - `source` means the coordinates were published by the page.
  - `geocoded` means OSM Nominatim matched the published address. `coord_precision` is `address`, `building_or_poi` or `street` (`street` = only the street matched).
- `url`, `checked_at`
- `hours` (string), `height_m`, `capacity`, `features` (list)
- `rates`: a list of rate objects (see below). Council rate kinds are mapped to the shared set, and the original value is kept in `source_kind`.
- `discounts`, `notes`
- `source_file`
- `also_listed_in`: duplicates absorbed from other files
- `extra`: source-specific fields that aren't part of the shared schema

Each rate object has:
- `kind`: one of `hourly`, `daily_max`, `early_bird`, `night`, `weekend`, `flat` or `other`
- `label`
- `price_aud`: the drive-up price
- `online_price_aud`: the online, app or membership price
- `days`
- `entry_window` and `exit_window`, written `HH:MM-HH:MM`. A leading `-` means "before" and a trailing `-` means "after".
- `duration_hours_from` and `duration_hours_to`
- `conditions`

`osm.json` (OpenStreetMap, about 5.8k car parks, no rates) is **not** merged. Use it as a separate map layer.

## Per-source files

| File | What | Report |
|---|---|---|
| `secure.json` | Secure Parking (67) | `secure_report.md` |
| `wilson.json` | Wilson Parking (45) | `wilson_report.md` |
| `other_operators.json` | Care Park, First Parking, Cornerstone, Nationwide, PriPark (87) | `other_operators_report.md` |
| `council_and_public.json` | BCC car parks, Translink park 'n' rides, hospitals, unis, airport (190) | `open_data_report.md` |
| `malls.json` | Shopping centres (59; no published coords) | `malls_report.md` |
| `osm.json` | OpenStreetMap amenity=parking | `open_data_report.md` |
| `geocode_cache.json` | Nominatim responses, keyed by query (© OpenStreetMap contributors, ODbL) | |

## Rebuild

Raw page captures live in `raw/`. That folder is gitignored (about 60 MB of third-party HTML), so a fresh clone has to re-fetch.

```bash
cd data/carparks
python3 scripts/fetch_other_operators.py      # polite: obeys robots.txt crawl-delays (Cornerstone 60 s → ~36 min)
python3 scripts/build_other_operators.py      # offline parse → other_operators.json (keeps earlier geocodes)
python3 scripts/geocode.py                    # Nominatim, 1 req/s, cached → Cornerstone lat/lng (+ mall coords in cache)
python3 scripts/build_council_and_public.py   # offline → council_and_public.json
python3 scripts/merge_carparks.py             # → carparks.json
```

Secure, Wilson, OSM and the malls have their own scripts and notes: `tools/secure_parse.py`, `raw/wilson/*.py`, `raw/osm/normalise_osm.py` and `scripts/fetch_malls.py`. The scripts under `raw/` are tracked; only the captures there are ignored.

**Duplicates** are merged only through the reviewed `SAME_AS` table in `merge_carparks.py`. A pair is flagged as a possible duplicate if:
- the two records share a street address, or
- they are within 150 m of each other and have similar names, or
- they are within 40 m of each other.

Any flagged pair that is in neither `SAME_AS` nor `NOT_SAME` is printed as `UNREVIEWED candidate`. Review those before trusting a refresh.

**Caveats:**
- Prices are point-in-time (see `checked_at`), so check on-site signage.
- PriPark rates were hand-transcribed from prose.
- Point Parking was not scraped because its robots.txt blocks AI agents.
- 21 records still have no coordinates (airport, QUT, UQ, Griffith, Mater/QCH and Bramston Tce), because their sources give no usable address.
