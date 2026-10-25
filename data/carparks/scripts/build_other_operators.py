#!/usr/bin/env python3
"""Build other_operators.json from the cached raw pages (offline).

Operators: Care Park, First Parking, Cornerstone Parking, Nationwide Parking, PriPark.
Run scripts/fetch_other_operators.py first to populate raw/<operator>/.
Then run scripts/geocode.py to fill Cornerstone lat/lng (pages publish none).

Output: other_operators.json - JSON array, same record shape as secure.json.
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oplib import (BASE, TM, checked_at, clean, days_of, dur, height, in_bbox, oneline, price,
                   raw_path, rate, record, t24, windows)
from fetch_other_operators import CORNERSTONE_SKIP, PRIPARK_EXCL

OUT = os.path.join(BASE, "other_operators.json")


def read(op, url):
    return open(raw_path(op, url), encoding='utf-8', errors='replace').read()


def locs(xml):
    return re.findall(r'<loc>(.*?)</loc>', xml)


# --------------------------------------------------------------------------- Care Park
CP_API = "https://www.carepark.com.au/wp-json/wp/v2/cp_parking?cp_state=75&per_page=100"


def cp_hours(a):
    if a.get('open_247') == 'true':
        return "24/7"
    parts = []
    for d in a.get('cp_care_park_post_opening_hours') or []:
        dn = d['cp_care_park_post_op_ho_days'].strip()[:3]
        if d.get('closed_24_hours'):
            parts.append(f"{dn}: closed")
        else:
            parts.append(f"{dn}: {(d['cp_care_park_post_op_ho_opening_time'] or '')[:5]}-"
                         f"{(d['cp_care_park_post_op_ho_closing_time'] or '')[:5]}")
    return '; '.join(parts) or None


def cp_kind(title):
    t = title.lower()
    if 'casual' in t: return 'hourly'
    if 'early' in t: return 'early_bird'
    if re.search('night|after ?hours|overnight|evening', t): return 'night'
    if re.search('weekend|saturday|sunday', t): return 'weekend'
    if re.search('motorbike|motorcycle', t): return 'other'
    return None


def build_carepark():
    out = []
    for x in json.loads(read('carepark', CP_API)):
        a = x['acf']; L = a['cp_care_park_post_location']
        if not in_bbox(L.get('lat'), L.get('lng')):
            continue
        info = oneline(clean(a.get('cp_care_park_post_more_info_sec') or ''))
        rates, feats, notes, disc = [], [], [], []
        for sec in a.get('cp_care_park_post_pri_rate') or []:
            title = oneline(sec.get('cp_care_park_po_pri_rate_title'))
            des = oneline(clean(sec.get('cp_care_park_po_pri_rate_des') or ''))
            rows = [r for r in (sec.get('cp_care_park_po_pri_rate_p_rate_rep') or [])
                    if (r['cp_care_park_po_pri_p_r_rep_hours'] or '').strip() or (r['cp_care_park_po_pri_p_r_rep_drive_up'] or '').strip()]
            k = cp_kind(title); tl = title.lower()
            if 'monthly' in tl:
                feats.append('monthly_parking'); continue
            if 'online booking' in tl or 'app' in tl:
                feats.append('online_booking' if 'online' in tl else 'pay_by_app')
                if des: notes.append(f"{title}: {des}")
                continue
            if k is None or not rows:
                notes.append(f"{title}: {des}"); continue
            ent, ext = windows(des); dys = days_of(des) or days_of(title)
            if k == 'weekend' and not dys: dys = 'Sat-Sun'
            for r in rows:
                lab = oneline(r['cp_care_park_po_pri_p_r_rep_hours'])
                du = r['cp_care_park_po_pri_p_r_rep_drive_up']; on = r['cp_care_park_po_pri_p_r_rep_online']
                p, o = price(du), price(on)
                if p is None and o is None:
                    notes.append(f"{title} / {lab}: drive-up '{oneline(du)}', online '{oneline(on)}' (no price)"); continue
                f, tt = dur(lab) if k == 'hourly' else (None, None)
                kk = 'daily_max' if (k == 'hourly' and tt is None and f is not None and 'max' in lab.lower()) else k
                d2 = dys
                if k == 'weekend' and lab.lower().startswith('saturday'): d2 = 'Sat'
                if k == 'weekend' and lab.lower().startswith('sunday'): d2 = 'Sun'
                cond = [des] if des else []
                if p is None and du and du.strip(): cond.append(f"Drive-up: {oneline(du)}")
                rates.append(rate(kk, f"{title} - {lab}" if lab else title, p, o, d2, ent, ext, f, tt, ' | '.join(cond) or None))
        cap = re.search(r'Number of Bays\s+(\d+)', info)
        hgt = re.search(r'Height Clearance\s+(\d+(?:\.\d+)?)\s*(?:Metres|m)', info, re.I)
        if re.search(r'height clearance:?\s*open air', info, re.I): feats.append('open_air')
        if re.search(r'licen[cs]e plate recognition|ticketless|pay by plate', info, re.I):
            feats.append('licence_plate_recognition' if re.search('plate', info, re.I) else 'ticketless')
        m = re.search(r'Payment Methods\s+(.*?)(?:Other Information|New Day|$)', info)
        if m: notes.append("Payment: " + m.group(1).strip())
        for pat in [r'New Day [^.]*\.?', r'Lost Ticket[^A-Z]*', r'Car Park Entry / Exit\s+(.*?)\s+(?:Number of Bays|Premier|$)']:
            mm = re.search(pat, info)
            if mm: notes.append(oneline(mm.group(0)))
        if any(r['online_price_aud'] is not None for r in rates):
            disc.append({"label": "Online / Care Park App booking rate",
                         "details": "Lower online_price_aud shown on the site for pre-booking via the Care Park AU app or app.carepark.com.au."})
        hm = float(hgt.group(1)) if hgt else None
        if hm is None:
            mm = re.search(r'(\d(?:\.\d)?)m height clearance', info)
            hm = float(mm.group(1)) if mm else None
        if 'Motorbike' in json.dumps(rates): feats.append('motorcycle_parking')
        out.append(record(id=f"carepark-{x['slug']}", source='carepark', operator='Care Park',
                          name=html.unescape(x['title']['rendered']), address=L.get('address'), lat=L.get('lat'), lng=L.get('lng'),
                          url=x['link'], checked_at=checked_at('carepark', CP_API), hours=cp_hours(a), height_m=hm,
                          capacity=int(cap.group(1)) if cap else None, features=sorted(set(feats)), rates=rates,
                          discounts=disc, notes=' || '.join(dict.fromkeys(notes)) or None))
    return out


# --------------------------------------------------------------------------- First Parking
def fp_parse(u):
    h = read('firstparking', u); s = clean(h)
    a = s.find('Get Directions'); b = s.find('Get directions in Google Maps'); body = s[a:b]
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    addr = next((l for l in lines if re.search(r', (Brisbane|[A-Za-z ]+), \d{4}$', l)), None)
    m = re.search(r"data-lat='(-?[\d.]+)' data-lng='(-?[\d.]+)'", h)
    cap = re.search(r'(\d[\d,]*)\s+Spaces', s)
    hgt = re.search(r'Height Clearance:\s*([\d.]+)\s*m', body)
    hrs = re.findall(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday):\s*([^\n]+)', body)
    hours = '24/7' if hrs and all('24' in v for _, v in hrs) else ('; '.join(f"{d[:3]}: {v.strip()}" for d, v in hrs) or None)
    if hrs and len(set(v.strip() for _, v in hrs)) == 1 and hours != '24/7':
        hours = f"Mon-Sun: {hrs[0][1].strip()}"
    dirs = re.search(r'Directions:\s*\n\s*([^\n]+)', body)
    rates, feats, notes = [], ['licence_plate_recognition'], []
    if dirs: notes.append('Directions: ' + dirs.group(1).strip())
    for bl in re.split(r'\n\s*FROM\b', body)[1:]:
        bt = oneline(bl)
        if re.search(r'Monthly Parking', bt[:40]):
            feats.append('monthly_parking'); continue
        if 'Staff Rate' in bt[:60]:
            notes.append(oneline(re.sub(r'^\$\s*', '', bt))[:300]); continue
        if 'Duration Drive Up Rate Express Rate' in bt:
            pre, post = bt.split('Duration Drive Up Rate Express Rate', 1)
            ent, ext = windows(re.sub(r'(Mon-Fri|Mon-Sun),\s*', '', pre))
            mm = re.search(r'Entry:\s*(Mon-Fri|Mon-Sun|Sat-Sun)?,?\s*' + TM + r'\s*-\s*' + TM, pre, re.I)
            if mm: ent = f"{t24(mm.group(2))}-{t24(mm.group(3))}"
            for dl, p1, p2 in re.findall(r'(\d[\d.]*(?:\+|-\d+)?\s*(?:mins|hours|hrs|min|hour))\s+(FREE|\$[\d.]+)\s+(FREE|\$[\d.]+)', post):
                f, t = dur(dl)
                rates.append(rate('hourly', f"Casual {dl}", price(p1), price(p2), days_of(pre), ent, ext, f, t,
                                  oneline(re.sub(r'^\S+\s+\S+\s+', '', pre))))
            continue
        if 'Drive Up Rate Express Rate' in bt:
            pre, post = bt.split('Drive Up Rate Express Rate'); ps = re.findall(r'(FREE|\$[\d.]+)', post)
            lab = re.sub(r'^\$[\d.]+\s*', '', pre).strip()
            kind = 'early_bird' if 'Early Bird' in lab else 'night' if 'Evening' in lab else 'weekend' if 'Weekend' in lab else 'other'
            mm = re.search(r'Entry:\s*(Mon-Fri|Mon-Sun)?,?\s*' + TM + r'\s*-\s*' + TM, lab, re.I)
            ent, ext = windows(lab)
            if mm: ent = f"{t24(mm.group(2))}-{t24(mm.group(3))}"
            dy = 'Mon-Fri' if 'Mon-Fri' in lab else ('Sat-Sun & public holidays' if 'Weekend & Public Holiday' in lab else days_of(lab))
            short = (lab.split('.')[0].split(' Entry')[0].strip() or lab[:40]).replace(' Pay per exit', '')
            rates.append(rate(kind, short, price(ps[0]) if ps else None, price(ps[1]) if len(ps) > 1 else None,
                              dy, ent, ext, None, None, lab))
            continue
        mm = re.match(r'\$\s*([\d.]+)?\s*(.+?)\s+(?:Flat Rate|24hr Flat Rate)\s+\$([\d.]+)\s*(.*)$', bt)
        if not mm:
            notes.append('UNPARSED: ' + bt[:200]); continue
        lab = mm.group(2).strip(); drive = float(mm.group(3)); rest = mm.group(4)
        mem = re.search(r'Free Membership Rate\s+Register Now\s+\$([\d.]+)', rest)
        cond = oneline(re.sub(r'^.*?Register Now\s+\$[\d.]+\s*', '', rest) if mem else re.sub(r'^(BOOK NOW|Book Now)\s*', '', rest))
        if 'Overnight' in lab:
            rates.append(rate('flat', 'Overnight & Hotel Parking (24hr, pre-book)', None, drive, None, None, None, 0, 24,
                              cond.split('Please note')[0].strip()))
            feats.append('hotel_overnight_prebook'); continue
        kind = {'Daily': 'daily_max', 'Evening': 'night', 'Weekend': 'weekend'}.get(lab, 'other')
        dy = ('Sat-Sun & public holidays' if 'Sat, Sun and Public Holidays' in cond else
              'Mon-Fri' if 'Mon-Fri' in cond else 'Mon-Sun' if 'Mon-Sun' in cond else None)
        ent, ext = windows(cond)
        rates.append(rate(kind, f"{lab} flat rate", drive, float(mem.group(1)) if mem else None, dy, ent, ext, None, None, cond))
    nm = re.search(r'\n\s*([^\n]+?)\s*\n\s*[\d,]+ Spaces', s) or re.search(r'Hotel & Overnight Parking \n\s*([^\n]+?)\s*\n', s)
    disc = [{"label": "First Parking Express membership (free)",
             "details": "Site advertises 'Save up to 20%' on drive-up rates with free Express membership (ticketless LPR, card auto-charged). "
                        "online_price_aud holds the Express/Free Membership rate shown on the page."}]
    return record(id='firstparking-' + u.rstrip('/').split('/')[-1], source='firstparking', operator='First Parking',
                  name=nm.group(1).strip() if nm else None, address=addr,
                  lat=float(m.group(1)) if m else None, lng=float(m.group(2)) if m else None, url=u,
                  checked_at=checked_at('firstparking', u), hours=hours, height_m=float(hgt.group(1)) if hgt else None,
                  capacity=int(cap.group(1).replace(',', '')) if cap else None, features=sorted(set(feats)), rates=rates,
                  discounts=disc, notes=' || '.join(notes) or None)


def build_firstparking():
    out = []
    for u in locs(read('firstparking', "https://www.firstparking.com.au/portfolio-sitemap.xml")):
        if u.rstrip('/') == "https://www.firstparking.com.au/locations":
            continue
        m = re.search(r"data-lat='(-?[\d.]+)' data-lng='(-?[\d.]+)'", read('firstparking', u))
        if m and in_bbox(float(m.group(1)), float(m.group(2))):
            out.append(fp_parse(u))
    return out


# --------------------------------------------------------------------------- Nationwide
def nw_parse(u):
    h = read('nationwide', u); s = clean(h)
    a = s.find('Enquire Now \n X'); b = s.find('Contact us 24 hours'); body = s[a + 15:b]
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    m = re.search(r'data-lat="(-?[\d.]+)" data-lng="(-?[\d.]+)"', h)
    hrs = re.findall(r'(?m)^\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d[^\n]*?|24 Hours)\s*$',
                     s.split('Get directions')[0])
    vals = set(v.strip() for _, v in hrs)
    hours = ('24/7' if vals == {'24 Hours'} else f"Mon-Sun: {next(iter(vals))}" if len(vals) == 1
             else '; '.join(f"{d[:3]}: {v.strip()}" for d, v in hrs) or None)
    rb = body.split('Parking Rates')[1].split('Information')[0]
    info = body.split('Information', 1)[1] if 'Information' in body else ''
    rates, notes, feats = [], [], []
    dys = 'Mon-Sun' if 'Monday - Sunday' in rb else None
    for l in [x.strip() for x in rb.split('\n') if x.strip()]:
        mm = re.match(r'(.*?)\s+\$([\d.]+)$', l)
        if not mm:
            if 'Monthly' in l: feats.append('monthly_parking')
            continue
        lab, p = mm.group(1), float(mm.group(2))
        if l.lower().startswith('early bird'):
            ent, ext = windows(lab)
            rates.append(rate('early_bird', lab, p, None, days_of(lab), ent, ext, None, None, lab)); continue
        f, t = dur(lab)
        rates.append(rate('daily_max' if 'daily maximum' in lab else 'hourly', lab, p, None, dys, None, None, f, t, None))
    il = oneline(info)
    if 'Number Plate Recognition' in il: feats.append('licence_plate_recognition')
    if 'Ticketless' in il: feats.append('ticketless')
    nd = re.search(r'New day charges commence at \w+', il)
    if nd: notes.append(nd.group(0))
    pm = re.search(r'Payment Method Accepted\s*(.*?)(?:New day|$)', il)
    if pm: notes.append('Payment: ' + pm.group(1).strip())
    hc = re.search(r'Height Clearance\s*[\d.]+m', il)
    return record(id='nationwide-' + u.rstrip('/').split('/')[-1], source='nationwide', operator='Nationwide Parking',
                  name=lines[0], address=lines[1], lat=float(m.group(1)) if m else None, lng=float(m.group(2)) if m else None,
                  url=u, checked_at=checked_at('nationwide', u), hours=hours, height_m=height(hc.group(0)) if hc else None,
                  capacity=None, features=sorted(set(feats)), rates=rates, discounts=[], notes=' || '.join(notes) or None)


def build_nationwide():
    q = read('nationwide', "https://nationwideparking.com.au/state/qld/")
    out = []
    for u in sorted(set(re.findall(r'href="(https://nationwideparking\.com\.au/car-parks/[^"#?]+)"', q))):
        m = re.search(r'data-lat="(-?[\d.]+)" data-lng="(-?[\d.]+)"', read('nationwide', u))
        if m and in_bbox(float(m.group(1)), float(m.group(2))):
            out.append(nw_parse(u))
    return out


# --------------------------------------------------------------------------- PriPark
# PriPark publishes rates as prose; these tables are hand-transcribed from the cached pages
# (verbatim text is kept in each record's notes). Re-check against the page when refreshing.
def H(lab, p, f, t, cond=None, days=None):
    return rate('hourly', lab, p, None, days, None, None, f, t, cond)


def F(lab, p, cond=None):
    return rate('flat', lab, p, None, None, None, None, None, None, cond)


def M(p, cond=None):
    return rate('other', 'Monthly parking (per month)', p, None, None, None, None, None, None, cond)


_herston = [H('0-15 minutes', 0.0, 0, 0.25), H('15 minutes - 3 hours', 11.0, 0.25, 3), H('3-6 hours', 13.0, 3, 6),
            H('6-12 hours', 15.0, 6, 12), H('12-24 hours', 18.0, 12, 24),
            rate('weekend', 'Weekend (12 hours)', 40.0, None, 'Sat-Sun', None, None, None, 12, None)]
PPR = {
    'car-park-herston-private-hospital-bowen-hills': _herston,
    'car-park-36-thomas-st-chermside': [F('All-day parking', 5.0)],
    'car-park-tryon-plaza-upper-mt-gravatt': [F('All-day parking', 10.0)],
    'car-park-64-manila-st-beenleigh': [H('0-2 hours (customers visiting the property)', 0.0, 0, 2, cond='2 hours free for customers visiting this property'), H('2-12 hours', 5.0, 2, 12)],
    'car-park-8-bellew-st-beenleigh': [F('All-day parking', 4.0)],
    'car-park-chermside-health-hub-chermside': [H('0-2 hours', 0.0, 0, 2), H('2-3 hours', 4.0, 2, 3), H('3-4 hours', 8.0, 3, 4), H('4-5 hours', 15.0, 4, 5), H('5+ hours', 20.0, 5, None)],
    'car-park-bridge-st-fortitude-valley': [H('0-2 hours', 10.0, 0, 2), H('2-3 hours', 15.0, 2, 3), H('3-4 hours', 20.0, 3, 4), H('4+ hours', 25.0, 4, None)],
    'car-park-wembley-rd-logan': [F('All-day parking', 4.0)],
    'car-park-capestone-village-mango-hill': [H('0-2 hours', 0.0, 0, 2), H('2-3 hours', 5.0, 2, 3), H('3-4 hours', 10.0, 3, 4), H('4-12 hours', 20.0, 4, 12)],
    'car-park-70-edward-st-spring-hill': [H('0-2 hours', 0.0, 0, 2), H('2-12 hours', 55.0, 2, 12)],
    'car-park-education-city-springfield': [H('0-3 hours', 3.0, 0, 3), H('3-12 hours', 5.0, 3, 12)],
    'car-park-springfield-health-hub-springfield': [H('0-2 hours', 3.0, 0, 2), H('2-3 hours', 5.0, 2, 3), H('3-4 hours', 8.0, 3, 4), H('4-12 hours', 10.0, 4, 12)],
    'car-park-westside-private-hospital-taringa': [H('0-3 hours', 0.0, 0, 3), H('3-4 hours', 8.0, 3, 4), H('4-5 hours', 15.0, 4, 5), H('5-7 hours', 25.0, 5, 7), H('7-24 hours', 50.0, 7, 24)],
    'car-park-yeerongpilly-green': [H('0-3 hours', 0.0, 0, 3), H('3-4 hours', 7.0, 3, 4), H('4-5 hours', 15.0, 4, 5), H('5-12 hours', 30.0, 5, 12)],
    'yoga-way-springfield-car-park': [M(110.0, 'Inclusive of GST; application and device fee $80')],
    'car-park-448-boundary-rd-springhill': [],
    'car-park-wynyard-and-middle-street-cleveland': [F('Daily parking (per day)', 6.0)],
    'car-park-paddington-kids-club': [H('20 min - 1 hr', 5.0, round(20 / 60, 4), 1, cond='Site does not state a rate for under 20 minutes'), H('1-2 hrs', 10.0, 1, 2), H('2-3 hrs', 20.0, 2, 3), H('3-4 hrs', 30.0, 3, 4), H('4-12 hrs', 40.0, 4, 12), M(280.0, 'Secure monthly parking')],
    'car-park-704-gympie-rd-chermside': [F('All-day parking', 8.0)],
    'car-park-21-murrajong-rd-springwood': [F('All-day parking', 6.0)],
    'car-park-given-terrace-paddington': [H('0-1.5 hours', 0.0, 0, 1.5), H('1.5-2.5 hours', 20.0, 1.5, 2.5), H('2.5-3.5 hours', 30.0, 2.5, 3.5), H('3.5-12 hours', 40.0, 3.5, 12)],
    '78-denman-st-greenslopes-car-park-pripark': [H('Up to 4 hours', 11.0, 0, 4), H('4-12 hours', 20.0, 4, 12)],
    'car-park-health-city-springfield': [H('0-1 hours', 0.0, 0, 1), H('1-2 hours', 5.0, 1, 2), H('2-4 hours', 7.0, 2, 4), H('4-8 hours', 10.0, 4, 8), H('5-24 hours', 19.0, 5, 24, cond='As published ("$19 for 5-24hours"); overlaps the 4-8 hour band - likely a typo for 8-24 hours')],
    'car-park-parkside-1-springfield': [H('0-30 mins', 0.0, 0, 0.5), H('30 min - 5 hr', 5.5, 0.5, 5), H('5-12 hrs', 10.5, 5, 12)],
    'car-park-brisbane-powerhouse-new-farm': [H('0-30 mins', 0.0, 0, 0.5), H('30 mins - 3 hrs', 10.0, 0.5, 3), H('3-12 hrs', 12.0, 3, 12), rate('night', 'Night rate (enter after 5pm)', 15.0, None, None, '17:00-', None, None, None, 'Enter after 5pm')],
    'car-park-north-lakes-central': [H('0-1 hr', 4.0, 0, 1), H('1-2 hrs', 5.0, 1, 2), H('2-3 hrs', 6.0, 2, 3), H('3-4 hrs', 9.0, 3, 4), H('4-12 hrs', 16.0, 4, 12), rate('night', 'Overnight parking', 10.0, None, None, None, None, None, None, None), M(130.0, 'From the separate Northlakes Central monthly page: $130 inc GST + $30 non-refundable application fee')],
    '31-cleveland-st-stones-corner-car-park': [F('All-day parking', 12.0)],
    '2244-logan-road-car-park': [M(110.0, 'Inc GST; $15 non-refundable application fee')],
    'car-park-parkside-2-springfield': [H('0-2 hrs', 4.0, 0, 2), H('2-12 hrs', 8.0, 2, 12)],
}
PP_MERGED = {'car-park-herston-private-hospital': 'car-park-herston-private-hospital-bowen-hills',
             'northlakes-central-car-park': 'car-park-north-lakes-central'}
PPA = {
    'car-park-herston-private-hospital-bowen-hills': '7 Wren St, Bowen Hills QLD',
    'car-park-36-thomas-st-chermside': '36 Thomas St, Chermside QLD',
    'car-park-tryon-plaza-upper-mt-gravatt': '9 Tryon St, Upper Mount Gravatt QLD (access from Tryon St and Palm Dale Lane)',
    'car-park-64-manila-st-beenleigh': '64 Manila St, Beenleigh QLD',
    'car-park-8-bellew-st-beenleigh': '8 Bellew St, Beenleigh QLD (opposite The Mall Shopping Centre)',
    'car-park-chermside-health-hub-chermside': '621 Gympie Rd, Chermside QLD',
    'car-park-bridge-st-fortitude-valley': '82 Bridge St, Fortitude Valley QLD',
    'car-park-wembley-rd-logan': '87 Wembley Rd, Logan QLD',
    'car-park-capestone-village-mango-hill': 'Capestone Blvd & Napier Ave, Mango Hill QLD',
    'car-park-70-edward-st-spring-hill': '70 Edward St, Spring Hill QLD',
    'car-park-education-city-springfield': 'Sinnathamby Blvd, Springfield QLD',
    'car-park-springfield-health-hub-springfield': '18-26 Springfield Lakes Blvd, Springfield Lakes QLD',
    'car-park-westside-private-hospital-taringa': '32 Morrow Street, Taringa QLD',
    'car-park-yeerongpilly-green': '26 Queens Way, Yeerongpilly QLD',
    'yoga-way-springfield-car-park': 'Yoga Way, Springfield QLD',
    'car-park-448-boundary-rd-springhill': '448 Boundary Rd, Spring Hill QLD',
    'car-park-wynyard-and-middle-street-cleveland': 'Cnr Wynyard St & Middle St, Cleveland QLD',
    'car-park-paddington-kids-club': 'Cnr Guthrie St & Given Tce, Paddington QLD',
    'car-park-704-gympie-rd-chermside': '704 Gympie Rd, Chermside QLD (access off Wallace St)',
    'car-park-21-murrajong-rd-springwood': '21 Murrajong Rd, Springwood QLD',
    'car-park-given-terrace-paddington': '183 Given Terrace, Paddington QLD (access from Princess St)',
    '78-denman-st-greenslopes-car-park-pripark': '78 Denman St, Greenslopes QLD',
    'car-park-health-city-springfield': 'Wellness Way, Springfield QLD',
    'car-park-parkside-1-springfield': 'Mary Mackenroth Ln, Springfield QLD',
    'car-park-brisbane-powerhouse-new-farm': '119 Lamington St, New Farm QLD',
    'car-park-north-lakes-central': '2 McLennan Court, North Lakes QLD',
    '31-cleveland-st-stones-corner-car-park': '31 Cleveland St, Stones Corner QLD',
    '2244-logan-road-car-park': '2244 Logan Road, Upper Mount Gravatt QLD',
    'car-park-parkside-2-springfield': 'Barry Alexander Dr, Springfield QLD',
}
PP_MONTHLY_ONLY = {'yoga-way-springfield-car-park', '2244-logan-road-car-park', 'car-park-448-boundary-rd-springhill'}


def pp_basic(u):
    h = read('pripark', u); s = clean(h)
    a = s.find('Contact us \n 1300 720 533 \n', 300); b = s.find('OVER 13 YEARS'); body = s[a + 28:b].strip()
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    name = re.sub(r'\s*[–-]\s*PriPark$', '', lines[0])
    rt = oneline(body.split('Rates', 1)[1].split('Location & How to Access')[0]) if 'Rates' in body else ''
    loc = oneline(body.split('Location & How to Access', 1)[1].split('Booking Options')[0]) if 'Location & How to Access' in body else ''
    m = re.search(r'!2d(1\d\d\.\d+)!3d(-\d+\.\d+)', h)
    return name, rt, loc, ((float(m.group(2)), float(m.group(1))) if m else (None, None)), body


def build_pripark():
    sm = read('pripark', "https://pripark.com.au/page-sitemap.xml")
    urls = [u for u in locs(sm) if 'car-park' in u and not PRIPARK_EXCL.search(u.rstrip('/').split('/')[-1])]
    out = []
    for u in urls:
        slug = u.rstrip('/').split('/')[-1]
        if slug in PP_MERGED:
            continue
        if slug not in PPR:
            print("WARNING: PriPark page without transcribed rates:", u, file=sys.stderr)
            continue
        n, rt, loc, (la, ln), body = pp_basic(u)
        if not in_bbox(la, ln):
            continue
        notes = [f"Rates text as published: {rt}"]
        if loc: notes.append(f"Location text: {loc}")
        notes.append("lat/lng taken from the Google Maps embed on the page (may be approximate).")
        if slug == 'car-park-chermside-health-hub-chermside':
            notes.append("Map embed coordinates are identical to the 36 Thomas St Chermside page - possibly copied; treat lat/lng as low confidence.")
        if slug == 'car-park-education-city-springfield':
            notes.append("Map embed coordinates identical to Parkside #1 Springfield page; low confidence.")
        for k, v in PP_MERGED.items():
            if v == slug: notes.append(f"Merged duplicate PriPark page: https://pripark.com.au/{k}/")
        feats = []
        if re.search('monthly', rt, re.I) or slug in PP_MONTHLY_ONLY or slug == 'car-park-north-lakes-central':
            feats.append('monthly_parking')
        if re.search('EV charging', body): feats.append('ev_charging')
        if re.search('undercover', body, re.I): feats.append('undercover')
        if slug in PP_MONTHLY_ONLY: feats.append('monthly_only')
        out.append(record(id='pripark-' + slug, source='pripark', operator='PriPark',
                          name=re.sub(r'\s+Car Park$', '', n).strip() + ' Car Park', address=PPA[slug], lat=la, lng=ln, url=u,
                          checked_at=checked_at('pripark', u), features=sorted(set(feats)), rates=PPR[slug], notes=' || '.join(notes)))
    return out


# --------------------------------------------------------------------------- Cornerstone
CS_LIST = "https://www.cornerstoneparking.com.au/car-parks/"


def cs_table(h):
    i = h.find('>Car Park Rates</h1>')
    if i < 0:
        return None, []
    j = h.find('Car Park Conditions', i); seg = h[i:j if j > 0 else i + 60000]
    k = seg.find('oxy-dynamic-list')
    hdr = [oneline(html.unescape(re.sub(r'<br\s*/?>', ' ', x))) for x in re.findall(r'<h1[^>]*>(.*?)</h1>', seg[:k], re.S)][1:]
    rows = []
    for chunk in re.split(r'<div[^>]*class="ct-new-columns" data-id=', seg[k:])[1:]:
        cells = [oneline(html.unescape(re.sub('<[^>]+>', '', c))) for c in re.findall(r'<span[^>]*class="ct-span"[^>]*>(.*?)</span>', chunk, re.S)]
        if cells: rows.append(cells)
    return hdr, rows


def cs_parse(u, listing_addr):
    h = read('cornerstone', u); s = clean(h)
    a = s.find('hello world!'); b = s.find('PRE-PAY DISCLAIMER'); t = s[a + 12:b]
    L = [l.strip() for l in t.split('\n') if l.strip()]
    name = L[0]
    addr = L[2] if len(L) > 2 and re.search(r'\d{4}|QLD|Q\b', L[2]) else listing_addr.get(name)

    def field(lbl):
        m = re.search(re.escape(lbl) + r'\s*:\s*\n(.*?)\n\s*(?:Max Height Clearance|Payment Options|Car Park Information|Car Parking Options)', t, re.S)
        return oneline(m.group(1)) if m else None
    hours = field('Operating Hours'); hc = field('Max Height Clearance'); pay = field('Payment Options')
    rates, feats, notes = [], [], []
    if pay: notes.append('Payment: ' + pay)
    tl = t.lower(); pre_desc = s.split('Car Park DESCRIPTION')[0]
    if 'monthly' in tl: feats.append('monthly_parking')
    if 'cellopark' in tl: feats.append('pay_by_app')
    if 'PRE-PAY ONLINE NOW' in t: feats.append('online_prepay')
    if 'undercover' in tl: feats.append('undercover')
    if re.search(r'open[- ]air', pre_desc, re.I) and ('open-air' in tl or 'open air' in tl): feats.append('open_air')
    if re.search(r'ev charg|electric vehicle', tl): feats.append('ev_charging')
    cond_txt = oneline(t.split('Car Park Conditions:', 1)[1].split('Car Park DESCRIPTION')[0]) if 'Car Park Conditions:' in t else ''
    cols, rows = cs_table(h)
    for cells in rows:
        lab = cells[0]; vals = cells[1:]
        if len(cols) == 1:
            p = price(vals[0]) if vals else None; o = p if 'ONLINE' in cols[0].upper() else None
        else:
            di = next((i for i, c in enumerate(cols) if 'DRIVE' in c.upper()), 0)
            oi = next((i for i, c in enumerate(cols) if 'ONLINE' in c.upper()), None)
            p = price(vals[di]) if di < len(vals) else None
            o = price(vals[oi]) if oi is not None and oi < len(vals) else None
        ll = lab.lower(); f, tt = dur(lab)
        if 'early bird' in ll: kind = 'early_bird'
        elif 'night' in ll or 'evening' in ll: kind = 'night'
        elif re.search('weekend|saturday|sunday', ll) and 'monday' not in ll: kind = 'weekend'
        elif 'motor' in ll: kind = 'other'
        elif re.search('reserved|month', ll): kind = 'other'
        elif tt is None and f is not None and re.search('max|per day|daily', ll): kind = 'daily_max'
        elif f is not None: kind = 'hourly'
        elif 'day' in ll: kind = 'flat'
        else: kind = 'other'
        dy = days_of(lab); ent = ext = None; cond = None
        if kind in ('early_bird', 'night'):
            key = 'Early Bird Conditions' if kind == 'early_bird' else 'Night Rate Conditions'
            m = re.search(re.escape(key) + r'(.*?)(?=Night Rate Conditions|Early Bird Conditions|Casual Parking Conditions|Weekend|Online Pre-Payment|RATES RECOMMENCE|Rates recommence|$)', cond_txt, re.I)
            if m:
                cond = m.group(1).strip(); ent, ext = windows(cond); dy = dy or days_of(cond)
            if kind == 'night' and not ent:
                m2 = re.search(r'from\s+' + TM, lab, re.I)
                if m2: ent = f"{t24(m2.group(1))}-"
        if kind == 'weekend' and not dy: dy = 'Sat-Sun'
        if dy is None and re.search(r'mon(day)?\s*(to|-)\s*fri', ll): dy = 'Mon-Fri'
        extra = []
        if 'reserved' in ll: extra.append('Monthly parking rate')
        if len(cols) == 1 and 'ONLINE' in cols[0].upper(): extra.append(f"Single site column '{cols[0]}'")
        if p is None and o is None:
            notes.append(f"Rate row '{lab}' had no price: {vals}"); continue
        hd = kind in ('hourly', 'daily_max')
        rates.append(rate(kind, lab, p, o, dy, ent, ext, f if hd else None, tt if hd else None,
                          ' | '.join([x for x in [cond] + extra if x]) or None))
    # label fix-ups
    for x in rates:
        ll = x['label'].lower()
        m = re.match(r'under\s+([\d.]+)\s*(hrs?|hours?)', ll)
        if m: x['kind'] = 'hourly'; x['duration_hours_from'] = 0.0; x['duration_hours_to'] = float(m.group(1))
        m = re.match(r'([\d.]+)\s*\+\s*mins', ll)
        if m: x['duration_hours_from'] = round(float(m.group(1)) / 60, 4)
        if 'maximum daily rate' in ll: x['kind'] = 'daily_max'
        if 'lost ticket' in ll: x['kind'] = 'other'; x['duration_hours_from'] = x['duration_hours_to'] = None
        if x['kind'] == 'early_bird' and not x['entry_window']:
            m = re.search(r'entry before\s+' + TM, ll)
            if m: x['entry_window'] = f"-{t24(m.group(1))}"
            m = re.search(r'exit after\s+' + TM, ll)
            if m: x['exit_window'] = f"{t24(m.group(1))}-"
    if cond_txt:
        notes.append('Conditions: ' + re.sub(r'Please note: Whilst we try.*?full refund\.', '', cond_txt).strip()[:900])
    if re.search(r'Max Height Clearance :\s*Open Air', s) and not (hc and height(hc)):
        notes.append('Height: open air, no height restriction')
    disc = []
    if any(r['online_price_aud'] is not None and r['price_aud'] is not None and r['online_price_aud'] < r['price_aud'] for r in rates):
        disc.append({"label": "Online pre-pay rate",
                     "details": "Pre-pay online at the lower online_price_aud (site: up to 14 days in advance; does not guarantee a space)."})
    opt = oneline(t.split('Car Parking Options:', 1)[1])[:30] if 'Car Parking Options:' in t else ''
    if not rates and opt.startswith('Monthly Parking'): feats.append('monthly_only')
    r = record(id='cornerstone-' + u.rstrip('/').split('/')[-1].replace('_', '-'), source='cornerstone',
               operator='Cornerstone Parking', name=name, address=addr, lat=None, lng=None, url=u,
               checked_at=checked_at('cornerstone', u), hours=hours, height_m=height(hc) if hc else None, capacity=None,
               features=sorted(set(feats)), rates=rates, discounts=disc, notes=' || '.join(notes) or None)
    # site-specific overrides from each page's conditions text
    if name == 'Astor Terrace Car Park':
        for x in r['rates']:
            if x['kind'] == 'early_bird':
                x.update(days='Mon-Fri', entry_window='04:00-09:00', exit_window='-21:00',
                         conditions='Available online only (astorterracecarpark.com.au/early-bird). Weekdays only. Enter between 4am and 9am, exit before 9pm.')
            if x['label'].startswith('Afternoon'):
                x.update(days='Mon-Sun', entry_window='16:00-00:00', exit_window='-09:00',
                         conditions='Enter between 4pm and midnight, exit before 9am the following day. Available 7 days.')
            if x['kind'] == 'weekend':
                x.update(entry_window='04:00-', exit_window='-04:00',
                         conditions='Weekend/Public Holidays (Brisbane only): enter after 4am, exit before 4am the following day.')
        r['notes'] += " || Site notes casual/visitor parking is via astorterracecarpark.com.au."
    if name == '6 James Street':
        r['notes'] += (" || Visitors to 6 James Street tenancies only; maximum stay 2 hours; breach notices issued otherwise. "
                       "No rate published (payment 'Not Applicable').")
    return r


def build_cornerstone():
    lst = read('cornerstone', CS_LIST)
    ls = [l.strip() for l in clean(lst).split('\n') if l.strip()]
    listing_addr = {ls[i]: ls[i + 3] for i in range(len(ls) - 3) if ls[i + 2] in ('QLD', 'NSW', 'SA')}
    links = sorted(set(re.findall(r'href="(https://www\.cornerstoneparking\.com\.au/car-parks/[^"#?]+)"', lst)))
    return [cs_parse(u, listing_addr) for u in links if u.rstrip('/').split('/')[-1] not in CORNERSTONE_SKIP]


# --------------------------------------------------------------------------- main
def main():
    recs = build_carepark() + build_firstparking() + build_cornerstone() + build_nationwide() + build_pripark()
    ids = [r['id'] for r in recs]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for r in recs:
        for x in r['rates']:
            for k in ('price_aud', 'online_price_aud', 'duration_hours_from', 'duration_hours_to'):
                if x[k] is not None: x[k] = float(x[k])
    # keep previously geocoded coordinates (scripts/geocode.py) so a rebuild doesn't drop them
    if os.path.exists(OUT):
        old = {r['id']: r for r in json.load(open(OUT))}
        for r in recs:
            o = old.get(r['id'])
            if r['lat'] is None and o and o.get('lat') is not None and 'geocoded' in (o.get('notes') or ''):
                r['lat'], r['lng'] = o['lat'], o['lng']
                r['notes'] = ((r['notes'] + ' || ') if r['notes'] else '') + o['notes'].split(' || ')[-1]
    json.dump(recs, open(OUT, 'w'), indent=2, ensure_ascii=False)
    print(f"wrote {len(recs)} car parks to {OUT}")


if __name__ == "__main__":
    main()
