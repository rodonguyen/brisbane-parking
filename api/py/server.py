from __future__ import annotations

import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

ROOT_API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_API))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from py import stripepay, supportdb
from py.bbox import validate_bbox
from py.cache import InsightCache
from py.clerkauth import ClerkVerifier
from py.db import connect
from py.insight import InsightEngine

DB_PATH = ROOT_API / "parking.db"
SUPPORTERS_DB_PATH = ROOT_API / "supporters.db"
CACHE_DIR = ROOT_API / ".cache"
WEBHOOK_PATH = "/api/support/webhook"

RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "600"))
IS_PROD = os.environ.get("BPF_ENV", "").strip().lower() in ("production", "prod")


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw == "*":
        return ["*"]
    if raw:
        return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-client sliding window (in-process; fine for single uvicorn)."""

    def __init__(self, app, *, max_requests: int, window_secs: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max(1, max_requests)
        self.window_secs = window_secs
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        if request.url.path == "/api/health":
            return await call_next(request)
        # Stripe retries webhooks and signs them; throttling only loses payment records.
        if request.url.path == WEBHOOK_PATH:
            return await call_next(request)

        now = time.monotonic()
        key = self._client_key(request)
        bucket = self._hits[key]
        cutoff = now - self.window_secs
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": str(self.window_secs)},
            )
        bucket.append(now)
        return await call_next(request)


if not DB_PATH.exists():
    raise SystemExit(
        f"Database not found at {DB_PATH}. Run: python -m py.ingest (from api/)"
    )

conn = connect(DB_PATH)
cache = InsightCache(CACHE_DIR)
engine = InsightEngine(conn, cache)

support_conn = supportdb.connect(SUPPORTERS_DB_PATH)
supportdb.init_schema(support_conn)
support_payments = stripepay.StripeSupport(
    os.environ.get("STRIPE_SECRET_KEY", ""),
    os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
)
clerk = ClerkVerifier(os.environ.get("CLERK_ISSUER", ""))

app = FastAPI(
    title="Brisbane Parking API",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, max_requests=RATE_LIMIT_PER_MIN)
# Map payloads are ~300 KB of repetitive JSON; gzip cuts them ~10x on mobile.
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.get("/api/health")
def health():
    try:
        conn.execute("SELECT 1").fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"ok": True, "service": "brisbane-parking-api"}


@app.get("/api/meta")
def meta():
    return engine.meta()


@app.get("/api/meters")
def list_meters(
    west: float | None = Query(None),
    south: float | None = Query(None),
    east: float | None = Query(None),
    north: float | None = Query(None),
    suburb: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=1000),
):
    w, s, e, n = validate_bbox(west, south, east, north)
    return engine.map_meters(
        west=w,
        south=s,
        east=e,
        north=n,
        suburb=suburb,
        limit=limit,
    )


@app.get("/api/meters/{meter_no}")
def meter_detail(meter_no: str):
    insight = engine.meter_insight(meter_no)
    if insight is None:
        raise HTTPException(status_code=404, detail="meter not found")
    return insight


class SupportSessionRequest(BaseModel):
    """`email` is only a prefill hint; identity comes from the verified Clerk token."""

    email: str | None = Field(default=None, max_length=stripepay.EMAIL_MAX_LEN)


@app.post("/api/support/session")
def create_support_session(payload: SupportSessionRequest, request: Request):
    if not support_payments.enabled:
        raise HTTPException(status_code=503, detail="support payments not configured")
    identity = clerk.identity(request.headers.get("authorization"))
    email = (identity.email if identity else None) or stripepay.clean_email(payload.email)
    try:
        client_secret = support_payments.create_session_secret(
            email=email,
            clerk_user_id=identity.user_id if identity else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="could not start checkout") from exc
    return {"client_secret": client_secret}


@app.get("/api/support/status")
def support_status(request: Request):
    identity = clerk.identity(request.headers.get("authorization"))
    if identity is None:
        return {"supporter": False}
    return {
        "supporter": supportdb.is_supporter(
            support_conn,
            clerk_user_id=identity.user_id,
            email=identity.email,
        )
    }


@app.post(WEBHOOK_PATH)
async def support_webhook(request: Request):
    if not support_payments.webhook_enabled:
        raise HTTPException(status_code=503, detail="support payments not configured")
    event = support_payments.parse_webhook(
        await request.body(), request.headers.get("stripe-signature", "")
    )
    if event is None:
        raise HTTPException(status_code=400, detail="invalid signature")
    supporter = stripepay.supporter_from_event(event)
    if supporter is not None:
        supportdb.record(support_conn, supporter)
    return {"received": True}


def main() -> None:
    import uvicorn

    uvicorn.run("py.server:app", host="127.0.0.1", port=8080, reload=False)


if __name__ == "__main__":
    main()
