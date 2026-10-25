"""Upload API sources to a remote host and prepare venv (DB copied separately)."""
from __future__ import annotations

import os
import shlex
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

SERVICE_ENV_VARS = ("CORS_ORIGINS", "BPF_ENV", "RATE_LIMIT_PER_MIN", "MAX_BBOX_SPAN_DEG")

ENV_HEADER = """# Service env for brisbane-parking-api (systemd EnvironmentFile).
# Seeded once from the deploying shell; later deploys never overwrite it.
# Full list of supported keys: repo root .env.example
"""

FILES = [
    "api/requirements.txt",
    "api/py/__init__.py",
    "api/py/bbox.py",
    "api/py/cache.py",
    "api/py/carparks.py",
    "api/py/clerkauth.py",
    "api/py/db.py",
    "api/py/hours.py",
    "api/py/ingest.py",
    "api/py/insight.py",
    "api/py/server.py",
    "api/py/stripepay.py",
    "api/py/supportdb.py",
    "api/py/timectx.py",
    "data/carparks/carparks.json",
]

UNIT = f"""[Unit]
Description=Brisbane Parking API
After=network.target

[Service]
Type=simple
User={USER}
WorkingDirectory={REMOTE_ROOT}/api
Environment=PATH={REMOTE_ROOT}/.venv/bin
EnvironmentFile=-{REMOTE_ROOT}/api/.env
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


def parse_env(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def ensure_env_file(sftp: paramiko.SFTPClient, remote: str) -> dict[str, str]:
    """Seed the service env once; the host copy stays authoritative after that."""
    try:
        with sftp.file(remote, "r") as fh:
            existing = parse_env(fh.read().decode("utf-8", errors="replace"))
        print(f"keep existing {remote} ({', '.join(sorted(existing)) or 'no values'})")
        return existing
    except FileNotFoundError:
        pass

    seeded = {}
    for name in SERVICE_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            seeded[name] = value
    with sftp.file(remote, "w") as fh:
        fh.write(ENV_HEADER + "".join(f"{k}={v}\n" for k, v in seeded.items()))
    sftp.chmod(remote, 0o600)
    print(f"seeded {remote} ({', '.join(seeded) or 'nothing set in this shell'})")
    return seeded


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

    sftp = client.open_sftp()
    for rel in FILES:
        local = LOCAL_ROOT / rel
        remote = f"{REMOTE_ROOT}/{rel}"
        ensure_dir(sftp, Path(remote).parent.as_posix().replace("\\", "/"))
        print("put", rel)
        sftp.put(str(local), remote)

    run(client, f"python3 -m venv {REMOTE_ROOT}/.venv")
    run(
        client,
        f"{REMOTE_ROOT}/.venv/bin/pip install -U pip && "
        f"{REMOTE_ROOT}/.venv/bin/pip install -r {REMOTE_ROOT}/api/requirements.txt",
    )

    service_env = ensure_env_file(sftp, f"{REMOTE_ROOT}/api/.env")

    unit_path = f"{REMOTE_ROOT}/brisbane-parking-api.service"
    with sftp.file(unit_path, "w") as fh:
        fh.write(UNIT)
    sftp.close()

    # Non-TTY SSH cannot prompt for sudo; pipe the login password.
    pw = shlex.quote(PASSWORD)
    run(
        client,
        f"printf '%s\\n' {pw} | sudo -S cp {REMOTE_ROOT}/brisbane-parking-api.service "
        "/etc/systemd/system/brisbane-parking-api.service && "
        f"printf '%s\\n' {pw} | sudo -S systemctl daemon-reload && "
        f"printf '%s\\n' {pw} | sudo -S systemctl restart brisbane-parking-api",
    )
    print("API sources deployed; brisbane-parking-api restarted (DB still needed if missing)")
    if not service_env.get("CORS_ORIGINS"):
        print(
            f"WARNING: no CORS_ORIGINS in {REMOTE_ROOT}/api/.env — the deployed site's "
            "browser fetches will be blocked until you set it and restart the service.",
            file=sys.stderr,
        )
    client.close()


if __name__ == "__main__":
    main()
