#!/usr/bin/env python3
"""Build data/carparks/wilson.json from cached Wilson Parking API + detail pages.

Inputs (all cached raw under this dir, nothing is refetched if cached):
  - GetParkingByLocation API (Brisbane CBD centre, distance=100km) -> structured car park JSON
  - each car park detail page HTML -> rate accordion blocks (online / drive-up / Spott columns),
    monthly subscription cards, EV charger block, page notices.
Every value below is copied/parsed from those fetched documents; unknowns stay null.
"""
import datetime as dt
import json
import os
import re
import sys

from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch  # noqa: E402

P = "https://www.wilsonparking.com.au"
API = (P + "/api/v2/GetParkingByLocation?pageid=23413&latitude=-27.46777640825&longitude=153.029420017695"
       "&carParkFeature=undefined&sort=undefined&distance=100")
BBOX = dict(lat=(-27.75, -27.0), lng=(152.65, 153.35))
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "wilson.json"))


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def html_text(s):
    return clean(BeautifulSoup(s or "", "lxml").get_text(" ")) if s else ""


def money(s):
    """'$41.75 - $45.75' -> (41.75, 45.75); '$10.00' -> (10.0, 10.0); '' -> (None, None)"""
    vals = [float(x.replace(",", "")) for x in re.findall(r"\$\s*([\d,]+(?:\.\d+)?)", s or "")]
    if not vals:
        return None, None
    return min(vals), max(vals)


def fetched_at(url):
    """ISO timestamp of when the URL was fetched (from fetch_log), fall back to cache mtime."""
    best = None
    for line in open(os.path.join(HERE, "fetch_log.jsonl")):
        r = json.loads(line)
        if r["url"] == url and r["status"] == 200:
            best = r["t"]
    if best is None:
        best = os.path.getmtime(fetch.cache_path(url))
    return dt.datetime.fromtimestamp(best, dt.timezone.utc).replace(microsecond=0).isoformat()


# ---------- detail page parsing ----------

def parse_blocks(s):
    out = []
    for it in s.select(".accordionBlock-item"):
        name = it.select_one(".item-name")
        if not name:
            continue
        content = it.select_one(".accordionBlock-item-content")
        hdr, rows, notes = [], [], []
        if content:
            for d in content.find_all("div", recursive=False):
                cls = d.get("class") or []
                if "parkingServiceBlock-timelist" in cls:
                    for r in d.find_all("div", recursive=False):
                        lab = r.select_one(".flex-1")
                        vals = [clean(v.get_text()) for v in r.select(".cell-w")]
                        rows.append([clean(lab.get_text()) if lab else "", vals])
                elif "d-flex" in cls and not hdr and not rows:
                    hdr = [clean(v.get_text()) for v in d.select(".cell-w")]
                else:
                    n = clean(d.get_text(" "))
                    if n:
                        notes.append(n)
        out.append(dict(name=clean(name.get_text()), hdr=hdr, rows=rows, notes=" ".join(notes)))
    return out


def parse_ev(s):
    evs = []
    for e in s.select(".ev-charger"):
        title = clean(e.find("h5").get_text()) if e.find("h5") else None
        evs.append({"type": title, "text": clean(e.get_text(" "))})
    return evs


def parse_monthly(s):
    res = []
    for card in s.select(".non-automated-parking > div"):
        h5 = card.find("h5")
        if not h5:
            continue
        t = clean(card.get_text(" "))
        day = re.search(r"\$([\d,.]+)/day", t)
        mon = re.search(r"\$([\d,.]+)/month", t)
        res.append({"product": clean(h5.get_text()),
                    "per_day_aud": float(day.group(1).replace(",", "")) if day else None,
                    "per_month_aud": float(mon.group(1).replace(",", "")) if mon else None,
                    "quote_only": ("Get Quote" in t) and not mon})
    return res


def parse_page(html):
    s = BeautifulSoup(html, "lxml")
    txt = clean(s.get_text(" "))
    m = re.search(r"Entry:\s*(.{0,200}?)\s*(?:gallery|Get Directions)", txt)
    notice = s.select_one(".parkingLocation-wysiwyg-wrapper")
    return {
        "blocks": parse_blocks(s),
        "ev": parse_ev(s),
        "monthly": parse_monthly(s),
        "entry_text": m.group(1) if m else None,
        "notice": clean(notice.get_text(" ")) if notice else None,
        "monthly_only": bool(re.search(r"monthly (?:subscription )?parking only|for permanent monthly parkers only",
                                       txt, re.I)),
    }


# ---------- rate normalisation ----------

DAYS_PAT = re.compile(r"\b(Mon(?:day)?\s*[-–]\s*Fri(?:day)?|Sat(?:urday)?\s*(?:[-–]|or|&)\s*Sun(?:day)?|Weeknights?|Weekends?|Sunday)\b", re.I)


def norm_days(label, block, notes):
    m = DAYS_PAT.search(label or "")
    d = None
    if m:
        g = m.group(1).lower()
        if g.startswith("mon") or g.startswith("weeknight"):
            d = "Mon-Fri"
        elif g.startswith("sat") or g.startswith("weekend"):
            d = "Sat-Sun"
        elif g == "sunday":
            d = "Sun"
    if d is None and block == "Weekend":
        d = "Sat-Sun"
    if d is None and re.search(r"Monday to Friday|Mon(?:day)?\s*[-–]\s*Fri", notes or "", re.I):
        d = "Mon-Fri"
    if d and d.startswith("Sat") and re.search(r"Public Holiday", notes or "", re.I):
        d += " + public holidays"
    return d


def hours_from_token(tok):
    tok = tok.replace(" ", "")
    m = re.match(r"([\d.]+)(min|mins|minutes)?", tok)
    if not m:
        return None
    v = float(m.group(1))
    return round(v / 60, 4) if m.group(2) else v


def parse_duration(label):
    """'0.0 - 1.0 hrs' -> (0,1); '3.0 + hrs' -> (3,None); '20 min - 1.0 hr' -> (0.3333,1)."""
    l = label.replace("–", "-").replace("1 .0", "1.0").replace("0.5 - 1 .0", "0.5 - 1.0")
    m = re.match(r"^\s*([\d.]+\s*(?:min|mins|minutes)?)\s*(?:hrs?|hours?)?\s*-\s*([\d.]+\s*(?:min|mins|minutes)?)\s*(?:hrs?|hours?|Hrs?)\b", l, re.I)
    if m:
        return hours_from_token(m.group(1)), hours_from_token(m.group(2))
    m = re.match(r"^\s*([\d.]+\s*(?:min|mins|minutes)?)\s*-\s*([\d.]+\s*(?:min|mins|minutes))\b", l, re.I)
    if m:
        return hours_from_token(m.group(1)), hours_from_token(m.group(2))
    m = re.match(r"^\s*([\d.]+)\s*(?:\+\s*(?:hrs?|hours?)|(?:hrs?|hours?)\s*\+)", l, re.I)
    if m:
        return float(m.group(1)), None
    return None


def windows(text):
    """Extract entry/exit windows from free text."""
    t = text or ""
    entry = exit_ = None
    m = re.search(r"Entry between ([^,]+?)(?:,|$)", t, re.I)
    if m:
        entry = "between " + clean(m.group(1))
    m2 = re.search(r"Exit between (.+?)(?:\(same day\)|$|\.)", t, re.I)
    if m2:
        exit_ = "between " + clean(m2.group(1)) + (" (same day)" if "same day" in t.lower() else "")
    if not entry:
        m = re.search(r"(?:enter|entry)\s+(?:after|from)\s+([0-9:]+\s*(?:am|pm|h)?|\d{4}h)", t, re.I)
        if m:
            entry = "after " + clean(m.group(1))
    if not exit_:
        m = re.search(r"exit\s+(?:before|by)\s+([0-9:]+\s*(?:am|pm|h)?|\d{4}h|midnight|12am)(\s*(?:the following day|next day|, next day))?", t, re.I)
        if m:
            exit_ = "before " + clean(m.group(1) + (m.group(2) or ""))
    return entry, exit_


def first_sentences(notes, n=3):
    """Keep the rule-bearing part of notes; drop generic prepay marketing boilerplate."""
    if not notes:
        return None
    boiler = [r"Please note that prepaying online does not provide.*$", r"Download the Wilson Parking App.*$",
              r"Click (?:here|the Prepay Now).*?(?:started\.?|App\.?)", r"Select the Prepay Now link below to get started\.?",
              r"Pay in advance to access the best possible rates\.?", r"Discount parking available online\.?"]
    t = notes
    for b in boiler:
        t = re.sub(b, "", t, flags=re.I)
    t = clean(t)
    return t or None


def mk(kind, label, price=None, online=None, rng=None, channel=None, days=None, entry=None, exit_=None,
       dfrom=None, dto=None, cond=None, block=None, days_count=None):
    r = {"kind": kind, "label": label, "price_aud": price, "online_price_aud": online,
         "days": days, "entry_window": entry, "exit_window": exit_,
         "duration_hours_from": dfrom, "duration_hours_to": dto, "conditions": cond,
         # extensions (documented in wilson_report.md)
         "channel": channel, "source_block": block}
    if rng and rng[0] is not None and rng[1] is not None and rng[0] != rng[1]:
        r["price_range_aud"] = [rng[0], rng[1]]
    if days_count is not None:
        r["days_count"] = days_count
    return r


def rates_from_blocks(blocks):
    rates = []
    for b in blocks:
        name, hdr, notes = b["name"], [h.lower() for h in b["hdr"]], b["notes"]
        cond_base = first_sentences(notes)
        is_spott = name == "Spott"
        is_prepay = name == "Prepay Online"
        prev_spott_saver = None
        for label, vals in b["rows"]:
            vals = [v for v in vals]
            # map columns
            online = drive = None
            rng = (None, None)
            if is_spott:
                lo, hi = money(vals[0] if vals else "")
                online, rng, channel = lo, (lo, hi), "spott_app"
            elif hdr == ["online", "drive up"]:
                lo, hi = money(vals[0] if vals else "")
                online, rng = lo, (lo, hi)
                if len(vals) > 1:
                    drive = money(vals[1])[0]
                channel = "online+drive_up" if (online is not None and drive is not None) else ("online" if online is not None else "drive_up")
            elif hdr == ["online"]:
                lo, hi = money(vals[0] if vals else "")
                online, rng, channel = lo, (lo, hi), "online"
            else:
                drive = money(vals[0] if vals else "")[0]
                channel = "drive_up"
            # also pick up a "varies from $a - $b" range stated in the label
            lr = money(label)
            if lr[0] is not None and lr[0] != lr[1] and "varies" in label.lower():
                rng = lr
            has_price = online is not None or drive is not None
            low = label.lower()

            # Spott: window row attaches to previous Spott Saver row
            if is_spott and not has_price:
                e, x = windows(label)
                if prev_spott_saver is not None and (e or x):
                    prev_spott_saver["entry_window"] = e
                    prev_spott_saver["exit_window"] = x
                    prev_spott_saver["conditions"] = clean((prev_spott_saver["conditions"] or "") + " " + label)
                continue
            if not has_price:
                # e.g. 'Hotel patrons*' w/o price or '0.0 - 1.0 hrs (tenant visitors only)' -> handled as discount
                continue

            dur = parse_duration(label)
            e, x = windows(label + " " + (notes or ""))
            days = norm_days(label, name, notes)
            spott_days = "Mon-Fri" if is_spott and dur else None

            if "spott saver" in low:
                r = mk("early_bird", label, None, online, rng, channel, days or ("Mon-Fri" if "mon - fri" in low else None),
                       None, None, None, None, cond_base, name)
                prev_spott_saver = r
                rates.append(r)
                continue
            if "flexi saver" in low:
                rates.append(mk("flat", label, None, online, rng, "online", None, None, None, None, None,
                                cond_base, name))
                continue
            m = re.match(r"^(\d+)\s*Days?(?: Cruise)?(?: from)?$", label, re.I)
            if m:
                rates.append(mk("other", label, drive, online, rng, channel, None, None, None, None, None,
                                cond_base, name, days_count=int(m.group(1))))
                continue
            if re.search(r"motor(?:bike|cycle)", low):
                rates.append(mk("other", label, drive, online, rng, channel, None, None, None, None, None,
                                cond_base, name))
                continue
            if "overnight" in low or "event" in low or "riverfire" in low or "market" in low or name == "Event Rate":
                kind = "other"
                cond = cond_base
                if name == "Event Rate" and dur:
                    rates.append(mk(kind, f"Event rate: {label}", drive, online, rng, channel, None, None, None,
                                    dur[0], dur[1], cond, name))
                else:
                    rates.append(mk(kind, label, drive, online, rng, channel, None, None, None, None, None, cond, name))
                continue
            if "hotel patron" in low:
                pv = drive if drive is not None else online
                rates.append(mk("other", label, pv, None, None, "hotel_patron", None, None, None, None, None,
                                " ".join(re.findall(r"\*?Hotel patrons[^.]*\.", notes)) or cond_base, name))
                continue
            if dur:
                dm = bool(re.search(r"daily maximum|max daily", low))
                if name == "Night":
                    rates.append(mk("night", label, drive, online, rng, channel, days, e, x, dur[0], dur[1], cond_base, name))
                else:
                    rates.append(mk("daily_max" if dm else "hourly", label, drive, online, rng, channel,
                                    spott_days or days, None, None, dur[0], dur[1], cond_base, name))
                continue
            if name == "Night" or "night" in low:
                ne, nx = (e, x)
                if is_spott or is_prepay:
                    ne, nx = windows(label)
                rates.append(mk("night", label, drive, online, rng, channel, days or ("Mon-Fri" if "mon - fri" in low else None),
                                ne, nx, None, None, cond_base, name))
                continue
            if name == "Weekend" or "weekend" in low or "sat" in low:
                we, wx = (e, x) if name == "Weekend" else (None, None)
                rates.append(mk("weekend", label, drive, online, rng, channel, days or "Sat-Sun", we, wx, None, None,
                                cond_base, name))
                continue
            if "entry after" in low:
                ee, _ = windows(label)
                rates.append(mk("flat", label, drive, online, rng, channel, days, ee, None, None, None, cond_base, name))
                continue
            if "flat" in low:
                rates.append(mk("flat", label, drive, online, rng, channel, days, e, x, None, None, cond_base, name))
                continue
            rates.append(mk("other", label, drive, online, rng, channel, days, None, None, None, None, cond_base, name))
    # dedupe: Prepay-Online summary rows for night/weekend duplicate the Night/Weekend block online column
    out = []
    for r in rates:
        if r["source_block"] == "Prepay Online" and r.get("days_count") is not None:
            if any(o is not r and o["source_block"] == "Daily" and o.get("days_count") == r["days_count"]
                   and o["online_price_aud"] == r["online_price_aud"] for o in rates):
                continue
        if r["source_block"] == "Prepay Online" and r["kind"] in ("night", "weekend"):
            dup = [o for o in rates if o is not r and o["kind"] == r["kind"] and o["source_block"] in ("Night", "Weekend")
                   and o["online_price_aud"] is not None and o["online_price_aud"] == r["online_price_aud"]]
            if dup:
                if r.get("price_range_aud") and not dup[0].get("price_range_aud"):
                    dup[0]["price_range_aud"] = r["price_range_aud"]
                continue
        out.append(r)
    return out


def discounts_for(api, page):
    d = []
    blocks = {b["name"]: b for b in page["blocks"]}
    if "Spott" in blocks:
        d.append({"label": "Spott (Wilson Parking App)", "details": first_sentences(blocks["Spott"]["notes"]) or blocks["Spott"]["notes"]})
    elif api.get("spottIsAvailable"):
        d.append({"label": "Spott (Wilson Parking App)", "details": "spottIsAvailable=true in Wilson API; no Spott rates listed on page"})
    if "Prepay Online" in blocks or api.get("canBookABay"):
        txt = blocks["Prepay Online"]["notes"] if "Prepay Online" in blocks else ""
        det = "Prepay online (Book a Bay)" + (": " + first_sentences(txt) if first_sentences(txt) else "")
        if re.search(r"include platform fee", txt, re.I) and not re.search(r"include platform fee", det, re.I):
            det += " Rates shown include platform fee."
        if "does not provide a reserved or guaranteed space" in txt:
            det += " Prepaying does not guarantee a space."
        d.append({"label": "Prepay online", "details": clean(det)})
    for b in page["blocks"]:
        if "Online rate only available when you pay with your phone via the Wilson Parking App" in b["notes"]:
            d.append({"label": "Wilson Parking App pay-by-phone rate", "details": b["notes"]})
            break
    if api.get("isWilsonOne"):
        d.append({"label": "Wilson Parking Card", "details": "Pay-as-you-go Wilson Parking Card accepted (isWilsonOne=true)."})
    for m in page["monthly"]:
        if m["per_month_aud"] is not None:
            d.append({"label": f"Monthly subscription - {m['product']}",
                      "details": f"${m['per_month_aud']:.2f}/month" + (f" (${m['per_day_aud']:.2f}/day*)" if m["per_day_aud"] else "")})
        elif m["quote_only"]:
            d.append({"label": f"Monthly subscription - {m['product']}", "details": "Get quote (price not listed)"})
    for b in page["blocks"]:
        for label, vals in b["rows"]:
            low = label.lower()
            if "tenant visitors" in low or "hotel patrons" in low:
                sent = re.findall(r"\*?[^.*]*(?:[Hh]otel patrons|[Tt]enant visitors)[^.]*\.", b["notes"])
                d.append({"label": label.rstrip("*"), "details": clean(" ".join(sent)) or None})
    return d


def hours_string(ot):
    if not ot:
        return None
    def fmt(o):
        if o.get("closed"):
            return "Closed"
        if o.get("is24_7"):
            return "24 hours"
        if o.get("opening") or o.get("closing"):
            return f"{o.get('opening')}-{o.get('closing')}"
        return None
    parts, grp = [], []
    order = [o for o in ot if o["day_TimePeriod"] not in ("Monthly", "Public Holiday")]
    for o in order:
        v = fmt(o)
        if grp and grp[-1][1] == v:
            grp[-1][0].append(o["day_TimePeriod"])
        else:
            grp.append([[o["day_TimePeriod"]], v])
    for days, v in grp:
        lab = days[0][:3] if len(days) == 1 else f"{days[0][:3]}-{days[-1][:3]}"
        parts.append(f"{lab} {v}")
    ph = [o for o in ot if o["day_TimePeriod"] == "Public Holiday"]
    if ph:
        parts.append(f"Public holidays {fmt(ph[0])}")
    mon = [o for o in ot if o["day_TimePeriod"] == "Monthly"]
    if mon:
        parts.append(f"Monthly subscribers {fmt(mon[0])}")
    return "; ".join(p for p in parts if p and not p.endswith("None")) or None


def build():
    api = json.loads(fetch.fetch(API))
    cps = api["carParks"]
    sel = [c for c in cps if BBOX["lat"][0] <= c["location"]["latitude"] <= BBOX["lat"][1]
           and BBOX["lng"][0] <= c["location"]["longitude"] <= BBOX["lng"][1]]
    out = []
    for c in sel:
        url = P + c["url"]
        html = fetch.fetch(url)
        page = parse_page(html) if html else {"blocks": [], "ev": [], "monthly": [], "entry_text": None,
                                              "notice": None, "monthly_only": False}
        loc = c["location"]
        region = (loc.get("region") or {}).get("name") or c["url"].strip("/").split("/")[-2].replace("-", " ").title()
        features = list(dict.fromkeys((c.get("carParkFeature") or [])))
        if c.get("evChargerIsAvailable") or any("Casual Charging" == e["type"] for e in page["ev"]):
            features.append("EV charging")
        if c.get("disabledParkingIsAvailable"):
            features.append("Disabled parking")
        if c.get("monthlyParkingServiceIsAvailable") and "Monthly Parking" not in features:
            features.append("Monthly Parking")
        rates = rates_from_blocks(page["blocks"])
        notes = []
        if page["notice"]:
            notes.append(page["notice"])
        if page["monthly_only"] or (not rates and not page["blocks"]):
            notes.append("Page lists no casual rates" + (" (monthly parking only per page text)" if page["monthly_only"] else ""))
        if page["entry_text"]:
            notes.append("Entry: " + page["entry_text"])
        if c.get("direction"):
            notes.append("Directions: " + clean(c["direction"]))
        for e in page["ev"]:
            if e["type"] == "Casual Charging":
                notes.append("EV: " + e["text"])
        ev = None
        if c.get("evChargerIsAvailable") or any(e["type"] == "Casual Charging" for e in page["ev"]):
            ev = True
        heights = [float(h) for h in re.findall(r"Height:\s*([\d.]+)\s*m", page["entry_text"] or "")]
        api_h = c.get("heightRestriction") or None  # API uses 0 when not stated
        height = min(heights) if heights else api_h
        if heights and api_h and abs(api_h - min(heights)) > 0.005:
            notes.append(f"Height conflict: page entry shows {min(heights):.2f}m, API heightRestriction {api_h}m (page value used)")
        rec = {
            "id": f"wilson-{c['carParkNumber']}" if c.get("carParkNumber") else "wilson-" + c["url"].strip("/").split("/")[-1],
            "source": "wilson",
            "operator": "Wilson Parking",
            "name": clean(c.get("carParkName") or c.get("name")),
            "address": clean(loc.get("address")),
            "suburb": region,
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "url": url,
            "checked_at": fetched_at(url),
            "hours": hours_string(c.get("openingTimes")),
            "height_m": height,
            "capacity": None,
            "features": features,
            "ev_charging": ev,
            "accessible_parking": True if c.get("disabledParkingIsAvailable") else None,
            "phone": c.get("phoneNumber"),
            "book_url": (f"https://prepay.wilsonparking.com.au/public/flow.htm?_flowId=makeBooking-flow&carParkCode={c['carParkNumber']}"
                         if c.get("canBookABay") and c.get("carParkNumber") else None),
            "from_price_aud": float(c["fromPrice"]) if c.get("fromPrice") not in (None, "") else None,
            "monthly": page["monthly"],
            "rates": rates,
            "discounts": discounts_for(c, page),
            "notes": " | ".join(notes) or None,
            "carpark_number": c.get("carParkNumber"),
        }
        out.append(rec)
    json.dump(out, open(OUT, "w"), indent=2, ensure_ascii=False)
    print("wrote", OUT, len(out))


if __name__ == "__main__":
    build()
