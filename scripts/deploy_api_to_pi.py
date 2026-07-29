"""Upload API sources to a remote host and prepare venv (DB copied separately)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

HOST = os.environ.get("PI_HOST")
USER = os.environ.get("PI_USER", "pi")
PASSWORD = os.environ.get("PI_PASSWORD")
if not HOST:
    raise SystemExit("Set PI_HOST")
if not PASSWORD:
    raise SystemExit("Set PI_PASSWORD")
REMOTE_ROOT = os.environ.get("PI_REMOTE_ROOT", f"/home/{USER}/brisbane-parking")
LOCAL_ROOT = Path(__file__).resolve().parents[1]

FILES = [
    "api/requirements.txt",
    "api/py/__init__.py",
    "api/py/cache.py",
    "api/py/db.py",
    "api/py/hours.py",
    "api/py/ingest.py",
    "api/py/insight.py",
    "api/py/server.py",
    "api/py/timectx.py",
]

UNIT = f"""[Unit]
Description=Brisbane Parking API
After=network.target

[Service]
Type=simple
User={USER}
WorkingDirectory={REMOTE_ROOT}/api
Environment=PATH={REMOTE_ROOT}/.venv/bin
ExecStart={REMOTE_ROOT}/.venv/bin/python -m uvicorn py.server:app --host 127.0.0.1 --port 8080
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
"""


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 300) -> None:
    print(f"$ {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        sys.stdout.buffer.write(out.encode("utf-8", errors="replace") + b"\n")
    if err.strip():
        sys.stderr.buffer.write(err.encode("utf-8", errors="replace") + b"\n")
    if code != 0:
        raise SystemExit(f"command failed ({code}): {cmd}")


def ensure_dir(sftp: paramiko.SFTPClient, remote: str) -> None:
    parts = remote.strip("/").split("/")
    cur = ""
    for part in parts:
        cur += "/" + part
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            sftp.mkdir(cur)


def main() -> None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        username=USER,
        password=PASSWORD,
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )

    run(client, f"mkdir -p {REMOTE_ROOT}/api/py {REMOTE_ROOT}/api/.cache")
    run(client, f"python3 -m venv {REMOTE_ROOT}/.venv")
    run(
        client,
        f"{REMOTE_ROOT}/.venv/bin/pip install -U pip fastapi 'uvicorn[standard]' pydantic",
    )

    sftp = client.open_sftp()
    for rel in FILES:
        local = LOCAL_ROOT / rel
        remote = f"{REMOTE_ROOT}/{rel}"
        ensure_dir(sftp, Path(remote).parent.as_posix().replace("\\", "/"))
        print("put", rel)
        sftp.put(str(local), remote)

    unit_path = f"{REMOTE_ROOT}/brisbane-parking-api.service"
    with sftp.file(unit_path, "w") as fh:
        fh.write(UNIT)
    sftp.close()

    run(
        client,
        f"sudo cp {REMOTE_ROOT}/brisbane-parking-api.service "
        "/etc/systemd/system/brisbane-parking-api.service && "
        "sudo systemctl daemon-reload",
    )
    print("API sources + systemd unit ready (DB still needed)")
    client.close()


if __name__ == "__main__":
    main()
