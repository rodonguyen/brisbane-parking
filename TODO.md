# TODO

Project follow-ups not tracked as GitHub issues.

## Supporter payments

- [ ] **Stripe webhook (production)** — In the [Stripe Dashboard](https://dashboard.stripe.com/webhooks), add endpoint `https://brisbane-parking.tailb8c08f.ts.net/api/support/webhook` for `checkout.session.completed`. Copy the signing secret to Pi `~/brisbane-parking/api/.env` as `STRIPE_WEBHOOK_SECRET`, then `sudo systemctl restart brisbane-parking-api`. See [DEPLOY.md](DEPLOY.md#supporter-payments-optional).
- [ ] **Verify supporter flow** — Test payment with `4242 4242 4242 4242` while signed in; confirm `/api/support/status` returns `{ "supporter": true }` and the coffee badge appears on the Clerk user button.
- [ ] **Back up `supporters.db`** — Keep `api/supporters.db` on the Pi backed up separately from `parking.db` (re-ingest must not wipe payment history).

## Later

- [ ] **Premium entitlements** — Supporter copy promises early access; wire real feature gates when premium features exist.
