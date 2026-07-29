# Data directory

Canonical location for Brisbane City Council open-data CSVs used by ingest.

## Required files

Place these here (preferred over the repo root):

- `brisbane-parking-meters.csv`
- `parking-occupancy-forecasting.csv`
- `parking-occupancy-forecasting-2025.csv` (optional but used for richer history)

Download from:

- https://data.brisbane.qld.gov.au/explore/dataset/brisbane-parking-meters
- https://data.brisbane.qld.gov.au/explore/dataset/parking-occupancy-forecasting

CSVs are gitignored. Field notes and dataset descriptions: `docs/`.

Ingest looks in `data/` first, then the repo root:

```bash
cd api && python -m py.ingest
```

© Brisbane City Council — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
