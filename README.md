# Brisbane Parking Finder

Map of Brisbane City Council paid parking meters with current-hour free-bay chance and a few high-signal historical charts.

## Layout

```
brisbane-parking/
├── web/                 # React + Vite + TypeScript frontend
├── api/
│   ├── py/              # Supported FastAPI runtime (ingest + server)
│   ├── src/             # Optional Rust/Axum reference implementation
│   ├── requirements.txt
│   └── parking.db       # Generated SQLite (gitignored)
├── data/                # Canonical place for BCC CSVs (gitignored) + dataset notes
├── LICENSE              # MIT (code)
└── NOTICE               # BCC CC BY 4.0 data attribution
```

## Stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, TypeScript, MapLibre, Recharts (`web/`) |
| API (supported) | Python FastAPI (`api/py/`) |
| API (optional) | Rust Axum (`api/src/`) — same routes/schema when your toolchain can build |
| Data | SQLite from BCC CSVs; 24h JSON cache under `api/.cache/` |

Python is the supported way to run the API (especially on Windows where cargo link/build may be blocked). Keep Rust sources in sync as a reference, not as the default path.

## Data

Download CSVs from [data.brisbane.qld.gov.au](https://data.brisbane.qld.gov.au/) and place them under **`data/`** (preferred):

| File | Dataset |
|---|---|
| `brisbane-parking-meters.csv` | [brisbane-parking-meters](https://data.brisbane.qld.gov.au/explore/dataset/brisbane-parking-meters) |
| `parking-occupancy-forecasting.csv` | [parking-occupancy-forecasting](https://data.brisbane.qld.gov.au/explore/dataset/parking-occupancy-forecasting) (current year) |
| `parking-occupancy-forecasting-2025.csv` | Same dataset, 2025 export if you use historical context |

Ingest also accepts the same filenames in the repo root as a fallback. Large CSVs and the SQLite DB are gitignored (~150MB+ of CSV). Dataset field notes live in `data/docs/`.

`OCCUPANCY_PRED` is a discrete 0–5 fullness score. Free chance = `(5 - score) / 5`.

Context features derived at ingest: weekday / weekend / QLD holiday, and season (DJF / MAM / JJA / SON).

## Setup

Prerequisites: Python 3.11+, Node 20+.

```bash
# 1) CSVs in data/ (see above)

# 2) Ingest once (several minutes for ~6M occupancy rows)
make ingest
# or: cd api && python -m pip install -r requirements.txt && python -m py.ingest

# 3) Dev (API :8080 + Vite :5173 with /api proxy)
make dev
# or separately:
#   make api
#   make web
```

Open http://127.0.0.1:5173

Root `npm` scripts also exist: `npm run ingest`, `npm run dev:api`, `npm run dev:web`.

### Rust (optional)

```bash
cd api
# Needs a working MSVC or MinGW toolchain (+ Defender exclusion for target/ on Windows)
cargo run --bin ingest
cargo run
```

## API

- `GET /api/health`
- `GET /api/meta` — clock, suburb list, meter count
- `GET /api/meters?west=&south=&east=&north=&suburb=&limit=250` — pins for the visible map viewport (cached 24h per bbox)
- `GET /api/meters/{meter_no}` — chance, today/typical series, day-class context, nearby better options

The map only requests meters inside the visible bounds (debounced on pan/zoom). Zoom out past ~12.8 and pins unload until you zoom back in.

Current-hour lookup order: exact forecast → same zone/hour/day-class/season average → zone-hour average.

## Licence & attribution

- **Code:** MIT — see `LICENSE`
- **Data:** © Brisbane City Council, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — see `NOTICE`

Sources:

- https://data.brisbane.qld.gov.au/explore/dataset/brisbane-parking-meters
- https://data.brisbane.qld.gov.au/explore/dataset/parking-occupancy-forecasting

## Deploy

Production is Netlify for the frontend plus a remote FastAPI + SQLite API. Set `VITE_API_BASE` to the public API origin. See [`DEPLOY.md`](DEPLOY.md) for the general steps.

Personal live URLs, host paths, and ops checklist: RodoVault `Projects/Brisbane-Parking-Finder.md` (outside this repo).

## Contributing

See `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`. Security reports: `SECURITY.md`.

**Agents / AI assistants:** start with [`AGENTS.md`](AGENTS.md) for a fast map of the repo, domain model, and which docs to open next.
