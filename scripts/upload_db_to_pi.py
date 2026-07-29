"""Stream parking.db to a remote host over SFTP with progress."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

HOST = os.environ.get("PI_HOST")
USER = os.environ.get("PI_USER", "pi")
PASSWORD = os.environ.get("PI_PASSWORD")
if not HOST:
    raise SystemExit("Set PI_HOST")
if not PASSWORD:
    raise SystemExit("Set PI_PASSWORD")
LOCAL_DB = Path(__file__).resolve().parents[1] / "api" / "parking.db"
REMOTE_ROOT = os.environ.get("PI_REMOTE_ROOT", f"/home/{USER}/brisbane-parking")
REMOTE_DB = f"{REMOTE_ROOT}/api/parking.db"


def main() -> None:
    if not LOCAL_DB.exists():
        raise SystemExit(f"missing {LOCAL_DB}")

    size = LOCAL_DB.stat().st_size
    print(f"Uploading {LOCAL_DB} ({size / 1e6:.1f} MB) -> {REMOTE_DB}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        username=USER,
        password=PASSWORD,
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
        banner_timeout=30,
    )
    sftp = client.open_sftp()
    # larger window for throughput
    sftp.get_channel().settimeout(300)

    sent = 0
    t0 = time.time()
    last = 0.0

    def cb(transferred: int, total: int) -> None:
        nonlocal sent, last
        sent = transferred
        now = time.time()
        if now - last < 2 and transferred < total:
            return
        last = now
        elapsed = max(now - t0, 0.001)
        mbps = (transferred / 1e6) / elapsed
        pct = 100.0 * transferred / total if total else 0
        print(f"  {pct:5.1f}%  {transferred/1e6:.1f}/{total/1e6:.1f} MB  {mbps:.2f} MB/s")

    # Upload to temp then rename
    tmp = REMOTE_DB + ".partial"
    sftp.put(str(LOCAL_DB), tmp, callback=cb)
    sftp.rename(tmp, REMOTE_DB)
    sftp.close()
    client.close()
    print(f"Done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
