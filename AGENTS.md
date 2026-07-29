# AGENTS.md — Brisbane Parking Finder

Quick orientation for coding agents. Prefer this over scanning the whole tree.

## What this is

Map of Brisbane City Council paid parking meters showing **next-hour free-bay chance**, plus detail charts from historical occupancy forecasts. Civic utility: map-first, small focused UI.

## Read next (by task)

| If you need… | Read |
|---|---|
| Setup, stack, API overview | [`README.md`](README.md) |
| PR / style / what not to commit | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| API run notes (Python vs Rust) | [`api/README.md`](api/README.md) |
| Where CSVs go | [`data/README.md`](data/README.md) |
| Dataset field meanings | [`data/docs/`](data/docs/) (`meter-locations.md`, `occupancy-forecasting.md`) |
| Licence / BCC attribution | [`LICENSE`](LICENSE), [`NOTICE`](NOTICE) |
| Frontend design taste | [`.agents/skills/design-taste-frontend/SKILL.md`](.agents/skills/design-taste-frontend/SKILL.md) |
| Production deploy (Netlify + remote API) | [`DEPLOY.md`](DEPLOY.md); personal ops: RodoVault `Projects/Brisbane-Parking-Finder.md` |

Do not invent secrets; local dev needs no API keys (see `.env.example`).

## Layout (where to edit)

```
web/src/
  App.tsx          # shell, meta, selection
  Landing.tsx      # landing / entry
  ParkingMap.tsx   # MapLibre map, viewport fetches, pins
  DetailPanel.tsx  # meter detail + Recharts
  api.ts           # fetch helpers + shared types
  index.css        # styles

api/py/            # SUPPORTED API — edit here by default
  server.py        # FastAPI routes
  insight.py       # map pins, meter insight, fallbacks
  ingest.py        # CSV → SQLite
  db.py            # schema + ingest helpers
  cache.py         # 24h JSON cache under api/.cache/
  timectx.py       # Brisbane clock, day_class, season, chance_free
  hours.py         # operating hours / parkability

api/src/           # Optional Rust/Axum mirror — keep parity if you change behaviour
data/              # CSVs (gitignored) + docs/
```

Python FastAPI is the supported runtime (especially on Windows). Rust is a reference, not the default path.

## Domain model (must know)

- **`OCCUPANCY_PRED`**: discrete 0–5 fullness. **Free chance** = `(5 - score) / 5` (see `timectx.chance_free`).
- Context at ingest / lookup: **weekday / weekend / QLD holiday**, **season** summer / autumn / winter / spring (southern hemisphere).
- Next-hour lookup order (`insight.resolve_occupancy`): exact forecast → same zone/hour/day-class/season avg → zone-hour avg.
- Map loads **viewport bbox only** (debounced). Zoom out past ~12.8 → pins unload.
- Cache: `api/.cache/` JSON, ~24h per key. DB: `api/parking.db` (both gitignored).

## Commands

```bash
# CSVs must be under data/ first (see data/README.md)
make ingest          # several minutes; ~6M occupancy rows
make api             # :8080
make web             # :5173, proxies /api → :8080
make dev             # both (bash api/run-dev.sh)

# Checks
cd web && npm run lint && npm run build
curl -s http://127.0.0.1:8080/api/health
```

Root `npm run ingest` / `dev:api` / `dev:web` also work.

## API surface (preserve)

- `GET /api/health`
- `GET /api/meta` — clock, suburbs, meter count
- `GET /api/meters?west=&south=&east=&north=&suburb=&limit=` — map pins (bbox required; max span ~0.5°)
- `GET /api/meters/{meter_no}` — chance, series, context, nearby

Vite proxies `/api` → `127.0.0.1:8080`. Optional API env: `CORS_ORIGINS`, `RATE_LIMIT_PER_MIN`, `BPF_ENV=production`.

## Conventions

- Small, focused changes; match local style; no drive-by refactors.
- Do not commit CSVs, `parking.db`, `.cache/`, `node_modules/`, `__pycache__/`.
- Changing chance / lookup / parkability → update `api/py/` first; sync Rust only if touching both.
- Changing map behaviour → `ParkingMap.tsx` + `api.ts` types.
- Changing detail charts / panel → `DetailPanel.tsx`.
- UI: map-first civic tone; use the design-taste skill for visual work.
- Chart y-axes for % chance: prefer **20% ticks** (`0,20,…,100`), leave room for labels (no negative left chart margins that clip ticks).

## Common pitfalls

1. **No DB** → server exits until `python -m py.ingest` from `api/`.
2. **CSVs missing** → put them in `data/` (repo root is fallback only).
3. **Empty map** → zoom in (≥ ~12.8) and wait for debounced bbox fetch; confirm API is up.
4. **Stale insight after logic change** → clear `api/.cache/` or wait for cache expiry.
5. **Windows + Rust** → prefer Python; cargo may be blocked by Defender / toolchain.
