#!/usr/bin/env python3
"""Polite fetcher for shopping-centre parking pages.

- obeys robots.txt (urllib.robotparser) for the given UA
- global rate limit: >= 1.1 s between requests
- normal browser UA
- caches raw responses under data/carparks/raw/malls/<id>__<n>.html (+ .meta.json)

Usage: fetch_malls.py targets.json   (list of {id, urls:[...]})
"""
import json, os, re, sys, time, hashlib, urllib.robotparser, urllib.parse
import urllib.request, urllib.error, ssl

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.normpath(os.path.join(HERE, "..", "raw", "malls"))
os.makedirs(RAW, exist_ok=True)
_last = [0.0]
_robots = {}


def _wait():
    d = time.time() - _last[0]
    if d < 1.1:
        time.sleep(1.1 - d)
    _last[0] = time.time()


def _get(url, timeout=25):
    _wait()
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.status, r.geturl(), r.read()


def allowed(url):
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            st, _, body = _get(base + "/robots.txt")
            rp.parse(body.decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                rp.disallow_all = True
            else:
                rp.allow_all = True
        except Exception:
            rp.allow_all = True
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def fetch(cid, url, n):
    path = os.path.join(RAW, f"{cid}__{n}.html")
    meta = path + ".meta.json"
    if os.path.exists(meta):
        return json.load(open(meta))
    m = {"id": cid, "url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    if not allowed(url):
        m["status"] = "robots_disallowed"
    else:
        try:
            st, final, body = _get(url)
            m.update(status=st, final_url=final, bytes=len(body), file=os.path.basename(path))
            open(path, "wb").write(body)
        except urllib.error.HTTPError as e:
            m["status"] = e.code
        except Exception as e:
            m["status"] = "error: " + repr(e)[:200]
    json.dump(m, open(meta, "w"), indent=1)
    return m


if __name__ == "__main__":
    targets = json.load(open(sys.argv[1]))
    for t in targets:
        for i, u in enumerate(t["urls"], start=t.get("start", 0)):
            m = fetch(t["id"], u, i)
            print(t["id"], i, m.get("status"), m.get("bytes"), u, flush=True)
