# Deploy

Production split: static frontend on Netlify, FastAPI + SQLite on a always-on host with a public HTTPS origin the browser can call.

## Frontend (Netlify)

- App root: `web/` (`netlify.toml` builds with `npm run build`, publishes `dist`, SPA fallback to `index.html`).
- Set **`VITE_API_BASE`** to the API origin (no trailing slash), e.g. `https://api.example.com`.
- Local Vite leaves this empty and proxies `/api` → `127.0.0.1:8080` (see `web/vite.config.ts`).
- Redeploy after changing `VITE_API_BASE` so the value is baked into the bundle.
- Optional **`VITE_STRIPE_PUBLISHABLE_KEY`** (`pk_…`) shows the tip jar in the topbar and footer; unset hides it. Secret keys are rejected by the client on purpose.

```bash
cd web
npx netlify-cli env:set VITE_API_BASE "https://YOUR-API-ORIGIN"
npx netlify-cli env:set VITE_CLERK_PUBLISHABLE_KEY "pk_…" --context production --context deploy-preview --context branch-deploy
npx netlify-cli env:set VITE_STRIPE_PUBLISHABLE_KEY "pk_…"
npx netlify-cli deploy --prod
```

**Continuous deployment:** the Netlify site `brisbane-parking-finder` is linked to GitHub `rodonguyen/brisbane-parking` (`master`, base directory `web/`). Pushes to `master` build and publish automatically. Required build env: `VITE_API_BASE`, `VITE_CLERK_PUBLISHABLE_KEY` (publishable `pk_` only). Manual CLI deploys still work as a fallback.

## API host

1. Ingest **where you have enough CPU/RAM** (`make ingest`) — produces `api/parking.db`. Prefer copying that DB to the API host rather than ingesting there.
2. Install deps (`api/requirements.txt` or equivalent venv), place `parking.db` next to `api/py/`.
3. Run uvicorn bound as you prefer; production example:

   ```bash
   cd api
   python -m uvicorn py.server:app --host 127.0.0.1 --port 8080
   ```

4. Put a public HTTPS reverse proxy / tunnel in front of that port so Netlify’s origin can `fetch` `/api/*`.
5. Set **`CORS_ORIGINS`** to your Netlify origin(s) (comma-separated, no trailing slash). Defaults are Vite localhost only.
6. For production, set **`BPF_ENV=production`** (disables OpenAPI docs) and keep uvicorn on `127.0.0.1`.
7. After changing chance/lookup logic, clear `api/.cache/` (or wait for ~24h expiry).

Helpers under `scripts/` upload sources/DB when `PI_HOST` and `PI_PASSWORD` are set (optional `PI_USER`, `PI_REMOTE_ROOT`). Do not commit real hostnames, IPs, or passwords.

## Supporter payments (optional)

Off unless `STRIPE_SECRET_KEY` is set on the API host. All of this is server-side; the browser only ever sees the publishable key.

1. `pip install -r api/requirements.txt` (adds `stripe` and `pyjwt[crypto]`).
2. On the API host set `STRIPE_SECRET_KEY` (prefer a **restricted key**, `rk_`, with write access to Checkout Sessions rather than a full `sk_`), and `CLERK_ISSUER` (your Clerk Frontend API origin, e.g. `https://your-app.clerk.accounts.dev`) so supporter payments attach to the signed-in account.
3. In the Stripe Dashboard add a webhook endpoint pointing at `https://YOUR-API-ORIGIN/api/support/webhook` for `checkout.session.completed` (add `checkout.session.async_payment_succeeded` if you enable delayed methods), then set the signing secret as `STRIPE_WEBHOOK_SECRET`.
4. Amount and wording default to A$5 and "Brisbane Parking supporter coffee"; override with `SUPPORT_AMOUNT_CENTS`, `SUPPORT_CURRENCY`, `SUPPORT_PRODUCT_NAME`.
5. Records land in `api/supporters.db`, kept separate from `parking.db` so re-ingesting or copying the parking DB can never wipe payment history. **Back it up separately.**

Local end-to-end test with the Stripe CLI:

```bash
stripe listen --forward-to http://127.0.0.1:8080/api/support/webhook
# use the whsec_… it prints as STRIPE_WEBHOOK_SECRET, restart the API, then pay with card 4242 4242 4242 4242
```

`deploy_api_to_pi.py` points the systemd unit at `api/.env` on the host (`EnvironmentFile`). That file is seeded once from `CORS_ORIGINS` / `BPF_ENV` / `RATE_LIMIT_PER_MIN` / `MAX_BBOX_SPAN_DEG` in the deploying shell, then left alone — edit it on the host and restart the service. Because the unit itself is regenerated on every deploy, `api/.env` is where service config must live to survive, and it is the one host file worth backing up.

## Checks

- `GET /api/health` on the public API origin (verifies SQLite)
- Open the Netlify site, zoom the map in past ~12.8, confirm pins load
