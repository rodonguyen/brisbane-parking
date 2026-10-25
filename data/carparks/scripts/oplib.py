import re, html, os, json, datetime

"""Shared parsing helpers for build_other_operators.py."""
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def raw_path(op, url):
    return f"{BASE}/raw/{op}/" + re.sub(r'[^A-Za-z0-9._-]', '_', url.split('://')[1])[:180]


def checked_at(op, url):
    p = raw_path(op, url)
    t = os.path.getmtime(p)
    return datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=10))).isoformat(timespec='seconds')


def clean(h):
    h = re.sub(r'<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>', '', h, flags=re.S)
    h = re.sub(r'<br\s*/?>|</p>|</li>|</h\d>|</tr>|</div>', '\n', h)
    h = re.sub(r'<[^>]+>', ' ', h)
    h = html.unescape(h)
    h = re.sub(r'[ \t\xa0]+', ' ', h)
    return re.sub(r'\n\s*\n+', '\n', h)


def oneline(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def price(s):
    if s is None:
        return None
    s = s.strip()
    if not s or re.fullmatch(r'-|n/?a|not available', s, re.I):
        return None
    if re.match(r'free\b', s, re.I):
        return 0.0
    m = re.search(r'\$\s*([\d,]+(?:\.\d+)?)', s) or re.fullmatch(r'([\d,]+(?:\.\d+)?)', s)
    return float(m.group(1).replace(',', '')) if m else None


UNIT = r'(min(?:ute)?s?|mins?|hours?|hrs?|hr|h)\b'


def dur(label):
    """Return (from_h, to_h) from a band label; (None, None) if not a duration."""
    l = (label or '').lower().replace('–', '-').replace('—', '-')
    toks = re.findall(r'(\d+(?:\.\d+)?)\s*(' + UNIT[1:-3] + r')?\s*(\+)?', l)
    toks = [(float(n), (u or ''), plus) for n, u, plus in toks]
    if not toks:
        return (None, None)
    # propagate units backwards
    units = [u for _, u, _ in toks]
    for i in range(len(units) - 1, -1, -1):
        if not units[i]:
            units[i] = units[i + 1] if i + 1 < len(units) else 'h'
    vals = [n / 60 if u.startswith('min') else n for (n, _, _), u in zip(toks, units)]
    vals = [round(v, 4) for v in vals]
    if toks[0][2] == '+' or re.search(r'over|more than|\bplus\b', l):
        return (vals[0], None)
    if re.search(r'up to', l) and len(vals) == 1:
        return (0.0, vals[0])
    if len(vals) >= 2:
        return (vals[0], vals[1])
    return (None, None)


def t24(s):
    s = s.strip().lower().replace('.', ':')
    m = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if s.startswith('midnight'):
        return '00:00'
    if ap == 'pm' and h != 12:
        h += 12
    if ap == 'am' and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}"


TM = r'(\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm)|midnight|noon)'


def windows(text):
    t = (text or '').lower().replace('–', '-')
    ent = ext = None
    m = re.search(r'ent(?:er|ry)\s*(?:between)?:?\s*' + TM + r'\s*(?:-|and|to)\s*' + TM, t)
    if m:
        ent = f"{t24(m.group(1))}-{t24(m.group(2))}"
    else:
        m = re.search(r'ent(?:er|ry)\s*(?:after|from):?\s*' + TM, t)
        if m:
            ent = f"{t24(m.group(1))}-"
    m = re.search(r'exit\s*(?:between)?:?\s*' + TM + r'\s*(?:-|and|to)\s*' + TM, t)
    if m:
        ext = f"{t24(m.group(1))}-{t24(m.group(2))}"
    else:
        m = re.search(r'exit\s*(?:before|by):?\s*' + TM, t)
        if m:
            ext = f"-{t24(m.group(1))}"
    return ent, ext


def days_of(text):
    t = (text or '').lower()
    if re.search(r'mon(day)?\s*(-|to)\s*sun', t):
        return 'Mon-Sun'
    if re.search(r'mon(day)?\s*(-|to)\s*fri', t):
        return 'Mon-Fri'
    if re.search(r'sat(urday)?,?\s*(&|and|-|to)\s*sun|weekend|sat, sun', t):
        return 'Sat-Sun' + (' & public holidays' if 'public hol' in t else '')
    if re.search(r'\bsaturday\b', t) and not re.search(r'sunday', t):
        return 'Sat'
    if re.search(r'\bsunday\b', t) and not re.search(r'saturday', t):
        return 'Sun'
    if re.search(r'\bfriday\b', t):
        return 'Fri'
    return None


def rate(kind, label, price_aud=None, online=None, days=None, entry=None, exit_=None, dfrom=None, dto=None, cond=None):
    return {"kind": kind, "label": label, "price_aud": price_aud, "online_price_aud": online, "days": days,
            "entry_window": entry, "exit_window": exit_, "duration_hours_from": dfrom, "duration_hours_to": dto,
            "conditions": cond}


def record(**kw):
    base = {"id": None, "source": None, "operator": None, "name": None, "address": None, "lat": None, "lng": None,
            "url": None, "checked_at": None, "hours": None, "height_m": None, "capacity": None, "features": [],
            "rates": [], "discounts": [], "notes": None}
    base.update(kw)
    return base


def in_bbox(lat, lng):
    return lat is not None and lng is not None and -27.75 <= lat <= -27.0 and 152.65 <= lng <= 153.35


def height(text):
    m = re.search(r'(\d(?:\.\d+)?)\s*(?:m\b|metres|meters)', text or '', re.I)
    return float(m.group(1)) if m else None
