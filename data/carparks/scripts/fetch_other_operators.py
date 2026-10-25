#!/usr/bin/env python3
"""Polite fetcher for the smaller Brisbane car-park operators.

Caches pages under data/carparks/raw/<operator>/ (filename = URL with
non-filename chars replaced by '_'). Already-cached files are not refetched.

Per-site politeness (from each robots.txt, checked 2026-10-25):
  carepark      no crawl-delay  -> 1.05 s gap   (AI *training* bots disallowed; reference use)
  firstparking  no crawl-delay  -> 1.05 s gap
  nationwide    no crawl-delay  -> 1.05 s gap
  pripark       Crawl-delay: 10 -> 10.5 s gap
  cornerstone   Crawl-delay: 60 -> 61 s gap   (~36 min for 35 pages)
Skipped: pointparking.com.au (robots.txt disallows Claude agents).

Usage: fetch_other_operators.py [operator ...]   (default: all)
"""
import os, re, subprocess, sys, time

UA = ("Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.normpath(os.path.join(HERE, "..", "raw"))
DELAY = {"carepark": 1.05, "firstparking": 1.05, "nationwide": 1.05, "pripark": 10.5, "cornerstone": 61}
_last = [0.0]


def raw_path(op, url):
    return os.path.join(RAW, op, re.sub(r'[^A-Za-z0-9._-]', '_', url.split('://')[1])[:180])


def fetch(url, op):
    p = raw_path(op, url)
    if os.path.exists(p):
        return open(p, encoding='utf-8', errors='replace').read()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    wait = DELAY[op] - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    r = subprocess.run(["curl", "-sL", "--compressed", "-A", UA, "-H", "Accept-Language: en-AU,en;q=0.9",
                        "-m", "30", "-o", p + ".tmp", "-w", "%{http_code}", url], capture_output=True, text=True)
    _last[0] = time.time()
    code = r.stdout.strip()
    print(op, code, url, flush=True)
    if code == "200":
        os.rename(p + ".tmp", p)
        return open(p, encoding='utf-8', errors='replace').read()
    if os.path.exists(p + ".tmp"):
        os.rename(p + ".tmp", f"{p}.{code}")
    if code in ("403", "429"):
        sys.exit(f"stopping: {code} from {op}")
    return ""


def locs(xml):
    return re.findall(r'<loc>(.*?)</loc>', xml)


def carepark():
    fetch("https://www.carepark.com.au/wp-json/wp/v2/cp_parking?cp_state=75&per_page=100", "carepark")


def firstparking():
    sm = fetch("https://www.firstparking.com.au/portfolio-sitemap.xml", "firstparking")
    for u in locs(sm):
        if u.rstrip('/') != "https://www.firstparking.com.au/locations":
            fetch(u, "firstparking")


def nationwide():
    q = fetch("https://nationwideparking.com.au/state/qld/", "nationwide")
    for u in sorted(set(re.findall(r'href="(https://nationwideparking\.com\.au/car-parks/[^"#?]+)"', q))):
        fetch(u, "nationwide")


PRIPARK_EXCL = re.compile(
    r'surfers|gold-coast|mackay|varsity|byron|main-beach|robina|southport|townsville|nepean|broadbeach|'
    r'marina-mirage|noosa|melbourne|budds|nti-parking|airshow|marathon|ekka|casual-parking|monthly-parking|'
    r'^car-park-(management|equipment|enforcement|consulting)|strata|revenue|contact|objection|privacy|policy|'
    r'calculator|workbook|licence|home-test|services|about|^pripark', re.I)


def pripark_urls():
    sm = fetch("https://pripark.com.au/page-sitemap.xml", "pripark")
    return [u for u in locs(sm) if 'car-park' in u and not PRIPARK_EXCL.search(u.rstrip('/').split('/')[-1])]


def pripark():
    for u in pripark_urls():
        fetch(u, "pripark")


CORNERSTONE_SKIP = {'aldi-norwood', 'griffith-airport', 'kirra_point', '114-old-pittwater-road', '120-old-pittwater-road'}


def cornerstone_urls():
    lst = fetch("https://www.cornerstoneparking.com.au/car-parks/", "cornerstone")
    links = sorted(set(re.findall(r'href="(https://www\.cornerstoneparking\.com\.au/car-parks/[^"#?]+)"', lst)))
    return [u for u in links if u.rstrip('/').split('/')[-1] not in CORNERSTONE_SKIP]


def cornerstone():
    for u in cornerstone_urls():
        fetch(u, "cornerstone")


if __name__ == "__main__":
    ops = sys.argv[1:] or ["carepark", "firstparking", "nationwide", "pripark", "cornerstone"]
    for op in ops:
        globals()[op]()
