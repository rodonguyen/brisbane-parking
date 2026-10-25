#!/usr/bin/env python3
"""Build data/carparks/council_and_public.json from raw captures in raw/council and raw/public.
Rates are transcribed verbatim from the official pages saved alongside (see each record's url / notes).
Anything not stated on a source page is null."""
import json, re, pathlib, datetime
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent.parent / "raw"  # raw captures
OUT = HERE.parent / "council_and_public.json"
CHECKED = "2026-10-25"


def R(kind, label, price, days=None, entry=None, exit_=None, dfrom=None, dto=None, cond=None, online=None):
    return {"kind": kind, "label": label, "price_aud": price, "online_price_aud": online, "days": days,
            "entry_window": entry, "exit_window": exit_, "duration_hours_from": dfrom,
            "duration_hours_to": dto, "conditions": cond}


def rec(**kw):
    base = {"id": None, "source": None, "operator": None, "name": None, "address": None, "lat": None, "lng": None,
            "url": None, "checked_at": CHECKED, "hours": None, "fee": None, "charge": None, "height_m": None,
            "capacity": None, "parking_type": None, "access": None, "features": {}, "rates": [], "discounts": [],
            "notes": None}
    base.update(kw)
    return base


BCC_URL = "https://www.brisbane.qld.gov.au/traffic-and-transport/parking-in-brisbane/car-parks"
live = json.loads((HERE / "council/brisbane-parking-stations_records.json").read_text())["results"][0]

ladder = [(0, 0.25, 0, "0-15 minutes"), (0.25, 1/3, 8, "15-20 minutes"), (1/3, 0.5, 15, "20-30 minutes"),
          (0.5, 1, 24, "30 minutes-1 hour"), (1, 1.5, 30, "1-1.5 hours"), (1.5, 2, 34, "1.5-2 hours"),
          (2, 2.5, 38, "2-2.5 hours"), (2.5, 3, 42, "2.5-3 hours"), (3, 3.5, 46, "3-3.5 hours"), (3.5, 4, 49, "3.5-4 hours")]

def weekday_ladder():
    return [R("hourly", lab, p, "Mon-Fri", "05:30-18:00", None, round(a, 4), round(b, 4)) for a, b, p, lab in ladder]

kgs_rates = weekday_ladder() + [
    R("max_daily", "Over 4 hours (entering before 4pm)", 49, "Mon-Fri", "before 16:00", None, 4, None),
    R("max_daily", "Maximum daily rate (leaving before 6pm)", 49, "Mon-Fri", None, "before 18:00"),
    R("max_daily", "Maximum daily rate (leaving before 5.30am the following day)", 64, "Mon-Fri", None, "before 05:30 next day"),
    R("early_bird", "Early bird", 28, "Mon-Fri", "05:30-07:00", "13:00-18:00"),
    R("evening", "Weekday evening, up to 4 hours", 10, "Mon-Fri", "from 16:00", None, 0, 4),
    R("evening", "Weekday evening, more than 4 hours (up to 5.30am)", 15, "Mon-Fri", "from 16:00", "before 05:30 next day", 4, None),
    R("weekend", "Weekend 0-3 hours", 10, "Sat-Sun", None, None, 0, 3, "5.30am Sat-5.30am Sun; 5.30am Sun-11pm Sun"),
    R("weekend", "Weekend 3-8 hours", 15, "Sat-Sun", None, None, 3, 8),
    R("weekend", "Weekend over 8 hours / maximum daily", 20, "Sat-Sun", None, None, 8, None),
    R("public_holiday", "Public holiday flat rate", 10, "Public holidays", "07:30-23:00", None, None, None, "per day"),
    R("motorcycle", "Motorcycle per day", 11, None, None, None, None, None, "flat entry; designated spaces Level B"),
    R("fee", "After-hours release fee", 50, None, None, "after closing", None, None, "in addition to parking fee"),
]
wt_rates = weekday_ladder() + [
    R("max_daily", "Over 4 hours (entering before 4.30pm)", 49, "Mon-Fri", "before 16:30", None, 4, None),
    R("max_daily", "Maximum daily rate (leaving before 6pm)", 49, "Mon-Fri", None, "before 18:00"),
    R("max_daily", "Maximum daily rate (leaving before 5.30am the following day)", 55, "Mon-Fri", None, "before 05:30 next day"),
    R("early_bird", "Early bird", 26, "Mon-Fri", "05:30-09:00", "13:00-19:00"),
    R("evening", "Weekday evening flat rate", 6, "Mon-Fri", "after 16:00", "before 05:30 next day"),
    R("weekend", "Weekend flat rate (per day)", 6, "Sat-Sun", None, None, None, None, "5.30am Saturday-5.30am Monday; max daily $6"),
    R("public_holiday", "Public holiday flat rate", 10, "Public holidays", None, None, None, None, "5.30am-5.30am, entry"),
    R("motorcycle", "Motorcycle per day", 11, None, None, None, None, None, "flat entry; designated spaces Level 2"),
    R("monthly", "Reserved monthly bay", 500, None, None, None, None, None, "allocation currently full (per council page)"),
]

out = [
    rec(id="bcc:king-george-square", source="brisbane_city_council", operator="Brisbane City Council",
        name="King George Square Car Park", address="100 Adelaide Street, Brisbane City Qld 4000 (entry only); 87 Roma Street (entry/exit)",
        lat=-27.4681503, lng=153.0242779, url=BCC_URL,
        hours="Mon-Thu 05:30-24:00; 05:30 Fri through to 23:00 Sun; PH 07:30-23:00 unless advised; closed Christmas Day and Good Friday",
        fee="yes", height_m=1.93, parking_type="underground", access="yes",
        features={"ev_charging": "free during opening hours, Level B", "capacity:disabled": "Level A (count not stated)",
                  "parent_pram_bays": "Level A", "payment": "cash (Level A pay station), Visa/Mastercard contactless, SKIDATA eCom LPR account",
                  "live_vacancy_dataset": "data.brisbane.qld.gov.au brisbane-parking-stations field king_george_square",
                  "live_vacant_spaces_snapshot": {"value": live.get("king_george_square"), "at": live.get("uploaded_to_open_data_at")}},
        rates=kgs_rates, discounts=["0-15 minutes free", "Early bird $28", "Evening $10/$15", "Weekend $10/$15/$20", "Public holiday $10"],
        notes="lat/lng from the Google Maps link on the council page (address geocode, not entrance). parking_type 'underground' taken from OSM osm:node/7027504446 (council page does not state it). Car park locks after closing; may open 24h at Council discretion."),
    rec(id="bcc:wickham-terrace", source="brisbane_city_council", operator="Brisbane City Council",
        name="Wickham Terrace Car Park", address="136 Wickham Terrace, Spring Hill Qld 4000",
        lat=-27.4649962, lng=153.0256328, url=BCC_URL, hours="24/7 (unmanned weekdays 21:00-05:30, weekends, public holidays)",
        fee="yes", height_m=1.93, parking_type="multi-storey", access="yes",
        features={"capacity:disabled": "Level 4 (count not stated)", "parent_pram_bays": "Level 4", "intercom": True,
                  "payment": "cash (Level 4 pay station), Visa/Mastercard contactless, SKIDATA eCom LPR account",
                  "live_vacancy_dataset": "data.brisbane.qld.gov.au brisbane-parking-stations field wickham_terrace",
                  "live_vacant_spaces_snapshot": {"value": live.get("wickham_terrace"), "at": live.get("uploaded_to_open_data_at")}},
        rates=wt_rates, discounts=["0-15 minutes free", "Early bird $26", "Evening $6", "Weekend $6/day", "Public holiday $10"],
        notes="lat/lng from the Google Maps link on the council page. parking_type 'multi-storey' taken from OSM osm:relation/16381172 (council page does not state it)."),
]

# ---- Hospitals ----
PAH_URL = "https://www.metrosouth.health.qld.gov.au/hospital-and-health-centres/princess-alexandra-hospital/parking-and-public-transport"
out.append(rec(id="hosp:pah-wilson", source="metro_south_health", operator="Wilson Parking",
    name="Princess Alexandra Hospital – Wilson Parking car park", address="Corner Ipswich Road and O'Keefe Street, Woolloongabba Qld 4102",
    url=PAH_URL, fee="yes", parking_type="multi-storey",
    features={"capacity:disabled": "level 4 (count not stated)", "concessional_parking": True, "card_surcharge_pct": 1.5},
    rates=[R("hourly", "0-30 minutes", 7, None, None, None, 0, 0.5), R("hourly", "30-60 minutes", 15, None, None, None, 0.5, 1),
           R("hourly", "1-1.5 hours", 21, None, None, None, 1, 1.5), R("hourly", "1.5-2 hours", 28, None, None, None, 1.5, 2),
           R("hourly", "2-3 hours", 35, None, None, None, 2, 3), R("max_daily", "3+ hours (daily maximum)", 37, None, None, None, 3, None),
           R("motorcycle", "Motorbike, max fee up to 24 hours", 18), R("multi_day", "5 day visitor pass", 85, None, None, None, None, None, "any 5 days or 5 consecutive days")],
    discounts=["Concessional parking for eligible patients/carers (apply at Information Desk, Building 1)"],
    notes="Rates 'as of 2 February 2026' per Metro South Health page. Cash not accepted. lat/lng not given by source."))
out.append(rec(id="hosp:pah-first", source="metro_south_health", operator="First Parking",
    name="Princess Alexandra Hospital – First Parking car park", address="Ipswich Road opposite the hospital, entry via Wolseley Street, Woolloongabba Qld 4102",
    url=PAH_URL, fee="yes", parking_type="multi-storey",
    rates=[R("max_daily", "Daily flat rate", 22, "Mon-Sun", "after 04:00", "before 04:00 next day", None, None, "pay per exit; charges recommence 4am",
             online=14.40)],
    discounts=["Express online booking saves 20% on casual rates (www.firstparking.com.au/express)"],
    notes="Rates 'as of 1 May 2026' per Metro South Health page; no concessional parking here. lat/lng not given by source."))

QCH_URL = "https://www.childrens.health.qld.gov.au/going-to-hospital/parking"
qch_rates = [R("hourly", "0-20 minutes", 0, None, None, None, 0, 1/3), R("hourly", "20 minutes-1 hour", 13, None, None, None, 1/3, 1),
             R("hourly", "1-1.5 hours", 20, None, None, None, 1, 1.5), R("hourly", "1.5-2 hours", 22, None, None, None, 1.5, 2),
             R("hourly", "2-3 hours", 25, None, None, None, 2, 3), R("hourly", "3-4 hours", 27, None, None, None, 3, 4),
             R("hourly", "4-5 hours", 28, None, None, None, 4, 5), R("hourly", "5-7 hours", 29, None, None, None, 5, 7),
             R("max_daily", "More than 7 hours", 38, None, None, None, 7, None), R("motorcycle", "Public motorbike", 10),
             R("day_pass", "Day pass (multi exit)", 38, None, None, None, None, None, "purchase from booth"),
             R("multi_day", "Multi day pass (3 or 5 days)", None, None, None, None, None, None, "$75-$120 range per source; purchase from booth"),
             R("fee", "Lost ticket", 45)]
for rid, name, entry, extra in [("hosp:qch-basement", "Queensland Children's Hospital basement car park", "entry on Raymond Terrace",
                                 {"height_m": 2.2, "features": {"capacity:disabled": 22, "disabled_bay_height_m": 2.5}}),
                                ("hosp:mater-hancock-st", "Mater Hancock Street car park", "entry on Hancock Street", {}),
                                ("hosp:mater-hill", "Mater Hill car park", "entry on Water Street and Stanley Street", {})]:
    r = rec(id=rid, source="childrens_health_queensland", operator="Mater Health Services", name=name,
            address=f"South Brisbane Qld 4101 ({entry})", url=QCH_URL, fee="yes", rates=qch_rates,
            discounts=["Concessional rate $12/day for eligible parents/carers (Patient and Family Travel Hub, Level 2)"],
            notes="Rate table on CHQ page applies to all 3 car parks (all operated by Mater Health Services). Page last updated Nov 2025. lat/lng not given.")
    r.update(extra)
    out.append(r)

RBWH_URL = "https://metronorth.health.qld.gov.au/rbwh/patients-and-visitors/parking-and-transport"
for rid, name, addr, op, url in [
    ("hosp:rbwh-butterfield", "RBWH Butterfield St Car Park (P1)", "20 Butterfield Street, Herston Qld 4006", "Wilson Parking", "https://www.wilsonparking.com.au"),
    ("hosp:rbwh-northern-p2", "RBWH Northern Car Park (P2)", "Kauri Pine Street, Herston Qld 4006", "Wilson Parking", "https://www.wilsonparking.com.au/parking-locations/queensland/herston/northern-car-park-royal-brisbane-womens-hospital-p2"),
    ("hosp:rbwh-herston-rd", "Herston Road Car Park", "325 Herston Road, Herston QLD 4006", "Wilson Parking", "https://www.wilsonparking.com.au/parking-locations/queensland/herston/herston-road-car-park/"),
    ("hosp:rbwh-bramston-tce", "Bramston Terrace Car Park", "Bramston Terrace (off Herston Road), Herston QLD 4006", "Point Parking", "https://pointparking.com.au/locations/bramston-terrace-herston/"),
    ("hosp:rbwh-royal-brisbane-cornerstone", "Royal Brisbane Carpark", "43 Butterfield Street, Herston QLD 4006", "Cornerstone Parking", "https://www.cornerstoneparking.com.au/car-parks/royal-brisbane-car-park-rbwh/")]:
    out.append(rec(id=rid, source="metro_north_health", operator=op, name=name, address=addr, url=url, fee="yes",
                   notes=f"Listed on {RBWH_URL}; hospital page defers rates/hours to operator website (not captured here). 'Charges will apply' per page."))

# ---- Airport ----
BNE = "https://www.bne.com.au/brisbane-airport-parking"
for rid, name, desc in [("bne:parkshort", "Brisbane Airport ParkShort", "Domestic Terminal car park Level 2; International Terminal open-air ground level; up to 4 hours; 24/7"),
                        ("bne:parklong", "Brisbane Airport ParkLong", "Domestic P1 Levels 5-9 and P2 Levels 1-6; International Terminal Levels 2-4 and outdoor area"),
                        ("bne:parkpremium", "Brisbane Airport ParkPremium", "Domestic; guaranteed undercover"),
                        ("bne:park-and-fly", "Brisbane Airport Park&Fly", "Domestic; express drop off and go"),
                        ("bne:parkvalet", "Brisbane Airport ParkValet", "International; valet"),
                        ("bne:airpark-undercover", "Brisbane Airport AIRPARK Undercover", "Domestic; free bus transfer 10-15 min"),
                        ("bne:airpark", "Brisbane Airport AIRPARK", "Domestic & International; open air; free bus transfer 15-30 min")]:
    out.append(rec(id=rid, source="brisbane_airport_corporation", operator="Brisbane Airport Corporation", name=name, url=BNE, fee="yes",
                   hours="24/7" if rid == "bne:parkshort" else None,
                   notes=f"{desc}. Prices are dynamic via online booking widget; no static rate table published (not captured)."))

# ---- Universities ----
UQ = "https://about.uq.edu.au/campuses-facilities/parking-transport-and-maps/parking-zones-rates-and-permits/parking-st-lucia"
uq_rates = [R("hourly", "Blue zone (outdoor) visitor", 1.65, "Mon-Fri", "07:00-21:00", None, None, None, "per hour; capped daily $8.20; up to 14h"),
            R("max_daily", "Blue zone (outdoor) visitor daily cap", 8.20, "Mon-Fri"),
            R("hourly", "Grey zone (undercover) visitor", 2.80, "Mon-Fri", "07:00-21:00", None, None, None, "per hour; capped daily $11.50; up to 14h"),
            R("max_daily", "Grey zone (undercover) visitor daily cap", 11.50, "Mon-Fri"),
            R("hourly", "Red zone visitor", 3.10, "Mon-Fri", "07:00-21:00", None, None, None, "per hour; capped daily $30.30; up to 14h"),
            R("max_daily", "Red zone visitor daily cap", 30.30, "Mon-Fri"),
            R("hourly", "Yellow zone (outdoor) visitor", 3.45, "Mon-Fri", "07:00-21:00", None, 0, 2, "no daily rate; max 2 hours"),
            R("motorcycle", "Orange zone motorcycle visitor daily", 1.35, "Mon-Fri")]
out.append(rec(id="uni:uq-st-lucia", source="university_of_queensland", operator="The University of Queensland", name="UQ St Lucia campus parking (zoned)",
               address="St Lucia Qld 4072", url=UQ, hours="Paid Mon-Fri 07:00-21:00; free outside these hours and weekends", fee="yes",
               rates=uq_rates, discounts=["Student rates: Blue $6.15/day, Grey $8.65/day", "Staff rates: Blue $6.40/day, Grey $9.10/day", "PWD permit parking free"],
               notes="Campus-wide zoned parking (many lots); single record. Pay via PayStay. Zone map PDF on UQ site."))
QUT = "https://www.qut.edu.au/about/campuses-and-facilities/parking"
for rid, nm, h in [("uni:qut-gp-p-block", "QUT Gardens Point – P Block (pay on exit)", 2.1), ("uni:qut-gp-szc-block", "QUT Gardens Point – SZC Block (pay on exit)", 2.0),
                   ("uni:qut-gp-under-freeway", "QUT Gardens Point – Under freeway car park (pay on exit)", 2.0), ("uni:qut-kg-f-block", "QUT Kelvin Grove – F Block (pay on exit)", 2.1),
                   ("uni:qut-kg-j-block", "QUT Kelvin Grove – J Block (pay on exit)", 2.1), ("uni:qut-kg-q-block", "QUT Kelvin Grove – Q Block (pay on exit)", 2.1),
                   ("uni:qut-kg-sports-lane", "QUT Kelvin Grove – Sports Lane (pay on exit)", None)]:
    note = "Casual rates not captured: QUT site behind Cloudflare challenge; text extract omitted the rate table."
    if "SZC" in nm or "Q Block" in nm:
        note += " Permit only 7am-4pm Mon-Fri; casual on weekday evenings and weekends."
    if "Sports Lane" in nm:
        note += " Open air, no height restriction."
    out.append(rec(id=rid, source="qut", operator="Queensland University of Technology", name=nm, url=QUT, fee="yes", height_m=h, access="yes", notes=note))
GU = "https://student.griffith.edu.au/uni-life/travel/parking-on-campus/casual-parking"
for rid, nm, sub in [("uni:griffith-nathan", "Griffith University Brisbane South (Nathan) casual parking", "Nathan Qld 4111"),
                     ("uni:griffith-mt-gravatt", "Griffith University Brisbane South (Mt Gravatt) casual parking", "Mount Gravatt Qld 4122")]:
    out.append(rec(id=rid, source="griffith_university", operator="Griffith University", name=nm, address=sub, url=GU, fee="yes",
                   parking_type="surface" if "Gravatt" in nm else None,
                   rates=[R("hourly", "Light purple zone (all-day casual)", 2, None, None, None, None, None, "per hour, max $6 per day"),
                          R("max_daily", "Light purple zone daily max", 6)],
                   notes="Pay via PayStay app or pay-by-plate machines. Two-hour metered zones also exist (rate not captured). Mt Gravatt is open-air only per FAQ. No parking at Brisbane City (South Bank) campus."))

# ---- TransLink park 'n' ride (KML) ----
ns = {"k": "http://www.opengis.net/kml/2.2"}
root = ET.parse(HERE / "public/translink_park_n_ride_locations.kml").getroot()
pnr = 0
for folder in root.iter("{http://www.opengis.net/kml/2.2}Folder"):
    region = folder.findtext("k:name", namespaces=ns)
    for pm in folder.findall("k:Placemark", ns):
        name = pm.findtext("k:name", namespaces=ns)
        addr = pm.findtext("k:address", namespaces=ns)
        desc = (pm.findtext("k:description", namespaces=ns) or "").strip()
        coords = pm.findtext(".//k:coordinates", namespaces=ns)
        lng = lat = None
        if coords:
            lng, lat = [float(x) for x in coords.strip().split(",")[:2]]
        m = re.search(r"(\d[\d,]*)\s+parking spaces", desc)
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        out.append(rec(id=f"translink-pnr:{slug}", source="translink_park_n_ride", operator=None, name=f"{name} park 'n' ride",
                       address=addr, lat=lat, lng=lng, url="https://translink.com.au/travel-with-us/parking",
                       capacity=int(m.group(1).replace(",", "")) if m else None, features={"park_ride": "yes", "translink_region": region},
                       notes=("description: " + desc if desc and not m else None) or
                             "Capacity approximate per Translink. Train station car parks managed by Queensland Rail; some bus/ferry by BCC. Fee not stated by source. Region list covers all SEQ, not only Brisbane."))
        pnr += 1

ids = [r["id"] for r in out]
dups = {i for i in ids if ids.count(i) > 1}
for r in out:
    if r["id"] in dups:
        r["id"] += f":{r['lat']},{r['lng']}"

meta = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "count": len(out),
        "park_n_ride_count": pnr,
        "sources": {"brisbane_city_council": {"url": BCC_URL, "licence": "Council website (© Brisbane City Council); live vacancies from dataset brisbane-parking-stations, CC BY 4.0"},
                    "translink_park_n_ride": {"url": "https://translink.com.au/sites/default/files/sites/default/files/assets/mapping/Park%20%27n%27%20ride%20locations_8%20%281%29.kml", "licence": "Not stated for the KML (© State of Queensland website); Translink open data (GTFS) is CC BY 4.0 but the KML is not part of it"},
                    "hospitals": {"licence": "© State of Queensland (Queensland Health) websites; facts transcribed"},
                    "airport": {"licence": "© Brisbane Airport Corporation website"},
                    "universities": {"licence": "University websites; facts transcribed"}}}
OUT.write_text(json.dumps({"meta": meta, "carparks": out}, indent=1, ensure_ascii=False))
print(OUT, len(out), "pnr", pnr)
