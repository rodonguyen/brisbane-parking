# Deploy

Production split: static frontend on Netlify, FastAPI + SQLite on a always-on host with a public HTTPS origin the browser can call.

## Frontend (Netlify)

- App root: `web/` (`netlify.toml` builds with `npm run build`, publishes `dist`, SPA fallback to `index.html`).
- Set **`VITE_API_BASE`** to the API origin (no trailing slash), e.g. `https://api.example.com`.
- Local Vite leaves this empty and proxies `/api` → `127.0.0.1:8080` (see `web/vite.config.ts`).
- Redeploy after changing `VITE_API_BASE` so the value is baked into the bundle.

```bash
cd web
npx netlify-cli env:set VITE_API_BASE "https://YOUR-API-ORIGIN"
npx netlify-cli deploy --prod
```

## API host

1. Ingest **where you have enough CPU/RAM** (`make ingest`) — produces `api/parking.db`. Prefer copying that DB to the API host rather than ingesting there.
2. Install deps (`api/requirements.txt` or equivalent venv), place `parking.db` next to `api/py/`.
3. Run uvicorn bound as you prefer; production example:

   ```bash
   cd api
   python -m uvicorn py.server:app --host 127.0.0.1 --port 8080
   ```

4. Put a public HTTPS reverse proxy / tunnel in front of that port so Netlify’s origin can `fetch` `/api/*`. CORS is already open on the API.
5. After changing chance/lookup logic, clear `api/.cache/` (or wait for ~24h expiry).

Helpers under `scripts/` upload sources/DB when `PI_HOST` and `PI_PASSWORD` are set (optional `PI_USER`, `PI_REMOTE_ROOT`). Do not commit real hostnames, IPs, or passwords.

## Checks

- `GET /api/health` on the public API origin
- Open the Netlify site, zoom the map in past ~12.8, confirm pins load
