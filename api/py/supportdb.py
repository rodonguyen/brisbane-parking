"""Supporter records.

Deliberately a separate SQLite file from parking.db: that one is rebuilt by ingest and
copied around during deploys (see DEPLOY.md), which would destroy payment history.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS supporters (
    checkout_session_id TEXT PRIMARY KEY,
    clerk_user_id TEXT,
    email TEXT,
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    paid_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_supporters_user ON supporters (clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_supporters_email ON supporters (email);
"""


@dataclass(frozen=True)
class Supporter:
    checkout_session_id: str
    clerk_user_id: str | None
    email: str | None
    amount_cents: int
    currency: str


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def record(conn: sqlite3.Connection, supporter: Supporter) -> bool:
    """Store a paid checkout. Returns False when Stripe replayed one we already have."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO supporters
           (checkout_session_id, clerk_user_id, email, amount_cents, currency, paid_at)
           VALUES (?,?,?,?,?,?)""",
        (
            supporter.checkout_session_id,
            supporter.clerk_user_id,
            (supporter.email or "").lower() or None,
            supporter.amount_cents,
            supporter.currency,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return cur.rowcount == 1


def is_supporter(
    conn: sqlite3.Connection,
    *,
    clerk_user_id: str | None,
    email: str | None,
) -> bool:
    """Email also counts, so paying before signing in still recognises the person."""
    clauses: list[str] = []
    args: list[str] = []
    if clerk_user_id:
        clauses.append("clerk_user_id = ?")
        args.append(clerk_user_id)
    if email:
        clauses.append("email = ?")
        args.append(email.strip().lower())
    if not clauses:
        return False
    row = conn.execute(
        f"SELECT 1 FROM supporters WHERE {' OR '.join(clauses)} LIMIT 1", args
    ).fetchone()
    return row is not None


def supporter_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM supporters").fetchone()
    return int(row["n"]) if row else 0
