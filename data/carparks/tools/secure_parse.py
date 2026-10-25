#!/usr/bin/env python3
"""Parse cached Secure Parking QLD car park pages into data/carparks/secure.json.

Input : data/carparks/raw/secure/page_<slug>.html (fetched from sitemap URLs)
Output: data/carparks/secure.json (Greater Brisbane bbox only) + stats on stdout.
No network access here; every field comes from the cached HTML.
"""
import glob, json, os, re, sys, datetime
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # data/carparks
RAW = os.path.join(BASE, 'raw', 'secure')
BBOX = dict(lat_min=-27.75, lat_max=-27.0, lng_min=152.65, lng_max=153.35)
URL_PREFIX = 'https://www.secureparking.com.au/en-au/car-parks/australia/qld/'

def txt(el):
    return re.sub(r'\s+', ' ', el.get_text(' ', strip=True)).strip() if el else None

def money(s):
    m = re.search(r'\$\s*([\d,]+(?:\.\d+)?)', s or '')
    return float(m.group(1).replace(',', '')) if m else None

def dur(label):
    """'0 Min - 30 Mins' -> (0,0.5); '2 Hours +' -> (2,None); else (None,None)."""
    def one(p):
        m = re.match(r'\s*([\d.]+)\s*(Min|Mins|Hour|Hours|Hr|Hrs)\b', p, re.I)
        if not m:
            return None
        v = float(m.group(1))
        return round(v / 60, 4) if m.group(2).lower().startswith('min') else v
    if '-' in label:
        a, b = label.split('-', 1)
        return one(a), one(b)
    if '+' in label:
        return one(label.split('+')[0]), None
    return None, None

def kind_for(title, row_label):
    t = title.lower(); r = (row_label or '').lower()
    if 'daily max' in r:
        return 'daily_max'
    if 'early bird' in t:
        return 'early_bird'
    if 'night' in t:
        return 'night'
    if 'weekend' in t or 'sunday' in t:
        return 'weekend'
    if 'hourly' in t:
        return 'hourly'
    if ('all day' in t or 'daily' in t) and r == 'flat rate':
        return 'flat'
    if 'all day' in t or 'daily' in t:
        return 'hourly' if dur(row_label)[0] is not None else 'flat'
    return 'other'

DISCOUNT_RX = re.compile(r'(?<![-\w])free\b|discount|validat|% off|voucher|cheaper|promo|concession|\bdeal\b', re.I)

def parse(path, checked_at):
    html = open(path, encoding='utf-8').read()
    soup = BeautifulSoup(html, 'lxml')
    slug = os.path.basename(path)[5:-5]
    rec = dict(id=None, source='secure', operator='Secure Parking', name=None, address=None,
               lat=None, lng=None, url=URL_PREFIX + slug + '/', checked_at=checked_at,
               hours=None, height_m=None, capacity=None, features=[], rates=[], discounts=[], notes=None)
    cta = soup.select_one('[data-carparkId], [data-carparkid]')
    if cta:
        rec['id'] = 'secure:' + cta.get('data-carparkid')
        try:
            rec['lat'] = float(cta.get('data-latitude')); rec['lng'] = float(cta.get('data-longitude'))
        except (TypeError, ValueError):
            pass
    else:
        rec['id'] = 'secure:' + slug
    if rec['lat'] is None:  # fallback: first entrance marker
        e = soup.select_one('.car-park-detail__entrance-item[data-latitude]')
        if e:
            rec['lat'] = float(e['data-latitude']); rec['lng'] = float(e['data-longitude'])
    content = soup.select_one('.car-park-detail__content')
    rec['name'] = txt(content.find('h1')) if content else None
    rec['address'] = txt(soup.select_one('.car-park-detail__address'))
    h = txt(soup.select_one('.car-park-detail__distance'))  # site renders clearance in this div
    m = re.match(r'^([\d.]+)\s*m$', h or '')
    rec['height_m'] = float(m.group(1)) if m and float(m.group(1)) > 0 else None  # 0.00m rendered when unknown
    entrances = [dict(name=txt(li), lat=float(li['data-latitude']), lng=float(li['data-longitude']))
                 for li in soup.select('.car-park-detail__entrance-item[data-latitude]')
                 if li.get('data-latitude')]
    # features
    hs = soup.find(id='car-park-services')
    if hs:
        ul = hs.find_next('ul')
        rec['features'] = [txt(li) for li in ul.find_all('li')]
    # opening hours
    oh = soup.select_one('h2.opening-hours')
    if oh:
        item = oh.find_parent(class_='car-park-detail__accordion-item')
        hours = {}
        for d in item.select('.dates-group > div'):
            day = d.select_one('.day')
            spans = d.find_all('span')
            if day and len(spans) > 1:
                hours[txt(day)] = txt(spans[1]).replace('\xa0', ' ')
        rec['hours'] = hours or None
    # rates
    rs = soup.select_one('.car-park-detail__rates-services')
    rates = []
    if rs:
        for it in rs.select('.car-park-detail__accordion-item'):
            title = txt(it.select_one('.car-park-detail__accordion-item-title'))
            sub = it.select_one('.car-park-detail__accordion-subitem')
            if not title or not sub:
                continue
            gen = {}
            g = sub.select_one('.general')
            if g:
                for d in g.find_all('div', recursive=False):
                    sp = d.find('span')
                    if sp:
                        k = txt(sp); gen[k] = txt(d)[len(k):].strip()
            desc_div = sub.find('div', recursive=False)
            desc = txt(desc_div) if desc_div and not desc_div.get('class') else None
            from_price = money(txt(it.select_one('.car-park-detail__accordion-item-add')))
            vf, vt = it.get('data-valid-from'), it.get('data-valid-to')
            special = it.get('data-is-special-day')
            for det in sub.select('.car-park-detail__accordion-subinfo .details'):
                row = txt(det.select_one('.time'))
                pricing = det.select_one('.pricing')
                online = drive = None; other_prices = []
                if pricing:
                    for p in pricing.find_all('div'):
                        t = txt(p)
                        if t.lower().startswith('online'):
                            online = money(t)
                        elif t.lower().startswith('drive'):
                            drive = money(t)
                        elif money(t) is not None:
                            other_prices.append(t)
                if online is None and drive is None and not other_prices:
                    # subscription rows (Monthly Parking - Enquire Now) carry no price
                    if title == 'Subscription Parking':
                        continue
                cond = []
                if desc: cond.append(desc)
                if drive is None and online is not None: cond.append('Online/pre-book price only (no drive-up price listed)')
                if other_prices: cond.append('Prices: ' + '; '.join(other_prices))
                if vf: cond.append(f'Valid {vf} to {vt}')
                if special == 'true': cond.append('Special-day product')
                if title == 'Hourly Parking' and row and row.strip().endswith('+') and 'daily max' not in row.lower():
                    cond.append('Open-ended top tier within this product window')
                d_from, d_to = dur(row or '')
                rates.append(dict(
                    kind=kind_for(title, row), label=f'{title} - {row}' if row else title,
                    price_aud=drive if drive is not None else (online if online is not None else (money(other_prices[0]) if other_prices else None)),
                    online_price_aud=online, days=gen.get('Available'),
                    entry_window=gen.get('Enter'), exit_window=gen.get('Exit'),
                    duration_hours_from=d_from, duration_hours_to=d_to,
                    conditions='; '.join(cond) or None))
    # monthly "from" price in description
    desc = soup.select_one('.car-park-detail__description')
    desc_text = txt(desc) or ''
    m = re.search(r'Monthly Parking from \$([\d,]+(?:\.\d+)?)\*?', desc_text)
    if m:
        cm = re.search(r'\*\s*(New customers only.*?Terms & conditions apply)', desc_text[m.end():])
        rates.append(dict(kind='other', label='Monthly Parking (from)', price_aud=float(m.group(1).replace(',', '')),
                          online_price_aud=None, days=None, entry_window=None, exit_window=None,
                          duration_hours_from=None, duration_hours_to=None,
                          conditions=('Per month; ' + cm.group(1).strip()) if cm else 'Per month'))
    seen_r = set(); rec['rates'] = [x for x in rates if not (json.dumps(x, sort_keys=True) in seen_r or seen_r.add(json.dumps(x, sort_keys=True)))]
    # discounts from description headings/paragraphs + services
    disc = []
    if desc:
        for el in desc.find_all(['h2', 'h3', 'p']):
            t = txt(el)
            if not t or 'New customers only' in t or 'Monthly Parking from' in t:
                continue
            for sent in re.split(r'(?<=[.!])\s+', t):
                if DISCOUNT_RX.search(sent) and not re.search(r'(hassle|stress)[ -]free', sent, re.I) and len(sent) < 400:
                    disc.append(dict(label=sent[:80].rstrip(' .'), details=sent))
    if 'Advantage Parker' in rec['features']:
        disc.append(dict(label='Advantage Parker', details='Car park listed as participating in Secure Parking "Advantage Parker" service (no details on page).'))
    # dedupe
    seen = set(); rec['discounts'] = [d for d in disc if not (d['details'] in seen or seen.add(d['details']))]
    # notes: entry/exit/important info
    notes = []
    imp = None
    for ci in soup.select('.cart-item__important'):
        ps = [txt(p) for p in ci.find_all('p') if txt(p)]
        if ps:
            imp = ps
    for it in soup.select('.car-park-detail__accordion-item'):
        t = txt(it.select_one('.car-park-detail__accordion-item-title'))
        if t in ('Entry Information', 'Exit Information'):
            v = txt(it.select_one('.car-park-detail__accordion-subitem'))
            if v: notes.append(f'{t}: {v}')
    if imp:
        notes.append('Important: ' + ' | '.join(imp))
    pn = re.search(r'Please note:?\s*(.{0,400}?)(?=\s*(?:\d\.|$))', desc_text)
    if pn:
        notes.append('Please note: ' + pn.group(1).strip())
    if entrances:
        notes.append('Entrances/exits: ' + '; '.join(f"{e['name']} ({e['lat']},{e['lng']})" for e in entrances))
    rec['notes'] = '\n'.join(notes) or None
    cap = re.search(r'(\d[\d,]*)\s*(?:car\s*)?(?:spaces|bays|car parks)\b', desc_text, re.I)
    rec['capacity'] = int(cap.group(1).replace(',', '')) if cap else None
    rec['_entrances'] = entrances
    return rec

def in_bbox(r):
    return r['lat'] is not None and BBOX['lat_min'] <= r['lat'] <= BBOX['lat_max'] and BBOX['lng_min'] <= r['lng'] <= BBOX['lng_max']

if __name__ == '__main__':
    out = []; allq = []
    for p in sorted(glob.glob(os.path.join(RAW, 'page_*.html'))):
        ts = datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).isoformat(timespec='seconds')
        r = parse(p, ts)
        allq.append(r)
        if in_bbox(r):
            r.pop('_entrances', None)
            out.append(r)
    out.sort(key=lambda r: r['name'] or '')
    json.dump(out, open(os.path.join(BASE, 'secure.json'), 'w'), indent=2, ensure_ascii=False)
    nocoord = [r['url'] for r in allq if r['lat'] is None]
    print(json.dumps(dict(qld_pages=len(allq), brisbane=len(out), qld_without_coords=nocoord,
                          outside=[(r['name'], r['lat'], r['lng']) for r in allq if r['lat'] is not None and not in_bbox(r)]), indent=1))
