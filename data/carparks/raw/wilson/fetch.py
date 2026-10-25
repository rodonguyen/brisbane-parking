#!/usr/bin/env python3
"""Polite cached fetcher: 1 req/s max, browser UA, caches raw responses under this dir."""
import hashlib, os, re, sys, time, urllib.request, urllib.error, json

UA = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "pages")
os.makedirs(CACHE, exist_ok=True)
LOG = os.path.join(HERE, "fetch_log.jsonl")
_last = [0.0]
_bad = [0]


def cache_path(url):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", url.split("://", 1)[-1]).strip("_")[:150]
    h = hashlib.sha1(url.encode()).hexdigest()[:8]
    return os.path.join(CACHE, f"{slug}_{h}.html")


def fetch(url, headers=None):
    p = cache_path(url)
    if os.path.exists(p):
        return open(p, encoding="utf-8", errors="replace").read()
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    import subprocess
    _last[0] = time.time()
    cmd = ["curl", "-s", "-L", "--compressed", "-A", UA, "-H", "Accept-Language: en-AU,en;q=0.9",
           "-w", "\n__HTTP_STATUS__%{http_code}", url]
    for k, v in (headers or {}).items():
        cmd[1:1] = ["-H", f"{k}: {v}"]
    out = subprocess.run(cmd, capture_output=True, timeout=60).stdout.decode("utf-8", errors="replace")
    body, _, code = out.rpartition("\n__HTTP_STATUS__")
    code = int(code or 0)
    if code != 200:
        body = None
    with open(LOG, "a") as f:
        f.write(json.dumps({"url": url, "status": code, "t": time.time()}) + "\n")
    if code in (403, 429):
        _bad[0] += 1
        if _bad[0] >= 3:
            raise SystemExit(f"STOP: repeated {code}")
        return None
    if body is None:
        return None
    _bad[0] = 0
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return body


if __name__ == "__main__":
    for u in sys.argv[1:]:
        b = fetch(u)
        print(u, len(b) if b else None, cache_path(u))
