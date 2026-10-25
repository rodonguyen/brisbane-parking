# Other operators: Greater Brisbane off-street car parks

Generated 2026-10-25 (AEST). Rebuild: `scripts/fetch_other_operators.py` → `scripts/build_other_operators.py` → `scripts/geocode.py`. Output: `data/carparks/other_operators.json`, a JSON array in the same shape as `secure.json` and `wilson.json`. Raw pages are cached under `data/carparks/raw/<operator>/`.

**Totals: 87 car parks; 77 have at least one priced rate.** Bounding box: lat -27.75..-27.0, lng 152.65..153.35. Coordinates come from operator pages, except the 35 Cornerstone sites, which were geocoded from their published addresses with OSM Nominatim (`scripts/geocode.py`, flagged in `notes`).

## Fill rates (count of records with a non-null value)

| operator | car parks | address | lat/lng | hours | height | capacity | features | with rates | rate rows | early bird | online price | discounts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carepark | 11 | 11 | 11 | 11 | 10 | 11 | 11 | 10 | 97 | 8 | 7 | 7 |
| firstparking | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 29 | 1 | 7 | 7 |
| cornerstone | 35 | 35 | 35 (geocoded) | 35 | 29 | 0 | 32 | 27 | 206 | 10 | 10 | 7 |
| nationwide | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 | 36 | 1 | 0 | 0 |
| pripark | 29 | 29 | 29 | 0 | 0 | 0 | 16 | 28 | 81 | 0 | 0 | 0 |

Car parks with no priced rate (10): carepark-348-edward-street-brisbane, cornerstone-100-edward-street, cornerstone-14-walden-lane, cornerstone-20-wyandra-street, cornerstone-240-st-pauls-terrace, cornerstone-333-ann-street, cornerstone-46-helen-street, cornerstone-57-coro-drive, cornerstone-6-james-street, pripark-car-park-448-boundary-rd-springhill. All are monthly-only sites, except 6 James St (visitor-only, max stay 2 h) and PriPark 448 Boundary Rd (authorised vehicles only).

## Per-operator method

### Care Park (`carepark`), www.carepark.com.au
- robots.txt: `User-agent: *` is allowed (Yoast block). A Cloudflare-managed block disallows named AI *training* crawlers (ClaudeBot, GPTBot, etc.). Content-Signal is `search=yes, ai-train=no, use=reference`. We fetched with a normal browser UA, for reference use only.
- Method: one call to the WordPress REST endpoint `/wp-json/wp/v2/cp_parking?cp_state=75&per_page=100` (state 75 = QLD) returned all 21 QLD car parks with structured ACF fields: geocoded location, open_247 / per-day hours, rate sections with drive-up and online columns, and a more-info block (bays, height, system, payment). 11 fall in the bbox. The rest are Gold Coast and Airlie Beach.
- Mapping: "Casual" → `hourly`. "Early Bird" → `early_bird`. Night / After-hours / Overnight → `night`. Weekend / Saturday / Sunday → `weekend`. Motorbike → `other`. Monthly and Online-Booking sections → features. The online/app price is stored in `online_price_aud`. A drive-up value of "Not Available" becomes `price_aud: null`.
- Problems: 348 Edward St is monthly-only, so no rates. Belmont Private Hospital is open air (height null). Amora "Overnight" shows only "-"/"N/A" values, so it is kept in notes. Some descriptions are free text, e.g. 344 Queen St "Weekend Parking" reads "Saturday & Sunday 6:00pm - 7:30am".

### First Parking (`firstparking`), www.firstparking.com.au
- robots.txt allows everything except wp-admin.
- Method: `portfolio-sitemap.xml` lists 20 location pages. We fetched all 20 and read coords from `data-lat` / `data-lng`. 7 are in Brisbane, at Fortitude Valley, the CBD, Spring Hill and Woolloongabba. Rate blocks were parsed from the page text.
- Drive-up price → `price_aud`. The "Express / Free Membership" rate (about 20% off) → `online_price_aud`, with a discount entry. "Overnight & Hotel Parking" is pre-book only, so its price sits in `online_price_aud` and `price_aud` is null.
- Problems: the PA Hospital staff rate has no price (email only) and is kept in notes. Monthly prices are never published.

### Cornerstone Parking (`cornerstone`), www.cornerstoneparking.com.au (discovered via web search; Brisbane-focused)
- robots.txt: `Disallow:` (empty) but **`Crawl-delay: 60`**. We obeyed it with a background fetcher sleeping 61 s per request: 35 pages over about 36 min, all HTTP 200.
- Method: the `/car-parks/` listing gives name, suburb, state and address for 40 sites. We dropped 5 outside QLD or Greater Brisbane (Brookvale ×2, Norwood, Griffith, Kirra). That leaves 35 Brisbane and Ipswich pages, parsed from the Oxygen-builder HTML rate table (STAY / RATE or DRIVE-UP / PRE-PAY ONLINE columns) plus the hours, height, payment and conditions fields.
- **No coordinates on any page** (only a Google Maps search link by address), so `lat`/`lng` were geocoded from the stated address via Nominatim. 3 needed query tweaks: St Paul's Tce (apostrophe), and 4 Walden Lane and 9 Browning St, which only matched as street (Walden Lane) or under South Brisbane (Browning St). The precision is recorded in each note. Inclusion relied on the stated QLD address. Capacity is not published.
- Problems: 7 sites are monthly-only (`features` includes `monthly_only`), and 6 James St is visitors-only with no price. Early-bird and night windows come from the "Conditions" text; Astor Terrace was hand-mapped from that text. 1 Park Road shows rates for a third party (Cornerstone says it doesn't manage casual parking there). Roma Street shows an online price above drive-up for 0-0.5 h ($10 vs $5), kept as published. "Lost Ticket" fees are `kind: other`.

### Nationwide Parking (`nationwide`), nationwideparking.com.au (discovered)
- robots.txt allows everything.
- Method: `car-parks-sitemap.xml` (88 pages) plus the `/state/qld/` page (10 QLD sites). Coords come from `data-lat` / `data-lng`. 5 are in the bbox: 85 North Quay, Boggo Road Village, Toowong Village & Tower, Woolworths Annerley and Woolworths Bulimba.
- Problems: no capacity, and no online prices or discounts. Toowong Village may duplicate the `malls.json` entry.

### PriPark (`pripark`), pripark.com.au (discovered)
- robots.txt: `Crawl-delay: 10`, obeyed (10.5 s per request).
- Method: `page-sitemap.xml`. We kept 31 car-park pages that are not obviously outside Brisbane (Gold Coast, Townsville, Mackay, Noosa, etc. were excluded by slug). Coords come from the Google Maps embed (`!2d lng !3d lat`) on each page, and all 31 are in the bbox. Rates are free-text sentences, so **rates were transcribed by hand from the cached page text into the schema**. The verbatim rate text is kept in `notes`.
- Two duplicate pages were merged: Herston Private Hospital (2 pages for 7 Wren St) and North Lakes Central (casual and monthly pages). That leaves 29 records.
- Problems: no hours, height or capacity on any page, and addresses come from the "Location & How to Access" sentence. Chermside Health Hub has the same embed coords as 36 Thomas St, and Education City the same as Parkside #1 (flagged low confidence). Health City Springfield publishes overlapping bands ("$10 for 4-8 hours and $19 for 5-24hours"), kept as published with a note. 4 sites are monthly-only or authorised-only.

## Operators checked but not included
- **Ace Parking**: robots allows everything except `/out/`. The `/find-parking/` list (about 60 locations) and the sitemaps hold only VIC, NSW and Geelong sites, with no Brisbane car park listed, although the footer mentions Brisbane. Result: 0.
- **InterPark**: `car-park-sitemap.xml` has 77 sites, all NSW and VIC. Result: 0.
- **careparking.com.au**: no DNS response; the real domain is carepark.com.au.
- **Point Parking** (pointparking.com.au, which has Brisbane sites such as Bramston Tce, Herston): **skipped on purpose**. Its robots.txt explicitly disallows `Claude-User`, `Claude-Code`, `ClaudeBot`, `anthropic-ai` and many other AI agents. Only robots.txt and the sitemap index were fetched before this was noticed.
- **Brisbane City Council** (King George Square, Wickham Terrace): parsed, then **left out** because `council_and_public.json` already covers both with rates. The raw page is cached in `raw/bcc/`.
- Not pursued: Kings Parking (appears only as a Yelp listing at 100 Edward St, which is a Cornerstone site), Divvy, Ezyparking and Share with Oscar (marketplaces, not operators), and hospital self-operated parking (Mater, RBWH).

## Known overlaps with other datasets
- Coorparoo Square (Cornerstone) and Toowong Village (Nationwide) also appear in `malls.json`. Dedupe by address when merging.
- The First Parking "67 Astor Tce / Wickham Terrace Car Park" is a different site from the BCC Wickham Terrace car park (136 Wickham Tce).

## Rate semantics
- `price_aud` is the drive-up / at-gate price. `online_price_aud` is the online pre-pay, app or membership price. When a site shows only one column headed "ONLINE RATE" (some Cornerstone sites, which pay by Cellopark app), the value goes into both fields and a condition note is added.
- Duration bands use `duration_hours_from` / `duration_hours_to`. An open-ended top band ("4+ hrs", "max fee per day") is `daily_max` with `duration_hours_to: null` where the label says max or per-day. Otherwise it stays `hourly` with `to: null`.
- `entry_window` / `exit_window` are `HH:MM-HH:MM`. A leading `-` means "before" and a trailing `-` means "after".
- `checked_at` is the raw file's fetch time (AEST).

## Samples

```json
{"id": "carepark-40-tank-street-brisbane", "name": "40 Tank Street, Brisbane", "address": "40 Tank Street, Brisbane City QLD, Australia", "lat": -27.4681362, "lng": 153.0198973, "hours": "24/7", "height_m": 2.0, "capacity": 300, "rates": [{"kind": "hourly", "label": "Casual Parking - 0.0 - 0.5 Hour", "price_aud": 25.0, "online_price_aud": 20.0, "days": "Mon-Fri", "entry_window": "05:00-", "exit_window": "-05:00", "duration_hours_from": 0.0, "duration_hours_to": 0.5, "conditions": "Monday - Friday Enter after: 5:00 am Exit before: 5:00 am, the next day"}, {"kind": "hourly", "label": "Casual Parking - 0.5 - 1.0 Hour", "price_aud": 46.0, "online_price_aud": 29.5, "days": "Mon-Fri", "entry_window": "05:00-", "exit_window": "-05:00", "duration_hours_from": 0.5, "duration_hours_to": 1.0, "conditions": "Monday - Friday Enter after: 5:00 am Exit before: 5:00 am, the next day"}, {"kind": "hourly", "label": "Casual Parking - 1.0 - 1.5 Hours", "price_aud": 67.0, "online_price_aud": 40.0, "days": "Mon-Fri", "entry_window": "05:00-", "exit_window": "-05:00", "duration_hours_from": 1.0, "duration_hours_to": 1.5, "conditions": "Monday - Friday Enter after: 5:00 am Exit before: 5:00 am, the next day"}]}
```

```json
{"id": "firstparking-valley-metro", "name": "Valley Metro", "address": "52 Alfred Street, Brisbane, 4006", "lat": -27.454834, "lng": 153.034184, "hours": "24/7", "height_m": 1.9, "capacity": 770, "rates": [{"kind": "early_bird", "label": "Early Bird", "price_aud": 22.0, "online_price_aud": 13.6, "days": "Mon-Fri", "entry_window": "04:00-10:00", "exit_window": "-23:59", "duration_hours_from": null, "duration_hours_to": null, "conditions": "Early Bird Entry: Mon-Fri, 4:00am-10:00am. Pay per exit. Exit before 11:59pm."}, {"kind": "hourly", "label": "Casual 0-15 mins", "price_aud": 0.0, "online_price_aud": 0.0, "days": "Mon-Fri", "entry_window": "10:00-16:00", "exit_window": null, "duration_hours_from": 0.0, "duration_hours_to": 0.25, "conditions": "Entry: Mon-Fri, 10:00am-4:00pm. Pay per exit. Charges recommence daily at 4:00am."}, {"kind": "hourly", "label": "Casual 15-60 mins", "price_aud": 21.0, "online_price_aud": 16.8, "days": "Mon-Fri", "entry_window": "10:00-16:00", "exit_window": null, "duration_hours_from": 0.25, "duration_hours_to": 1.0, "conditions": "Entry: Mon-Fri, 10:00am-4:00pm. Pay per exit. Charges recommence daily at 4:00am."}]}
```

```json
{"id": "cornerstone-300-ann-street", "name": "300 Ann Street", "address": "300 Ann Street, Brisbane QLD 4000", "lat": null, "lng": null, "hours": "Drive-Up - Monday to Friday, 6am to 6pm (Excluding public holidays) Online Pre-Pay - 24/7 Access (using online pre-pay pin code) (Including public holidays)", "height_m": 1.9, "capacity": null, "rates": [{"kind": "hourly", "label": "0 - 15 Mins", "price_aud": 9.0, "online_price_aud": null, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 0.0, "duration_hours_to": 0.25, "conditions": null}, {"kind": "hourly", "label": "15 - 30 Mins", "price_aud": 17.0, "online_price_aud": 15.0, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 0.25, "duration_hours_to": 0.5, "conditions": null}, {"kind": "hourly", "label": "30 Mins - 1 Hr", "price_aud": 35.0, "online_price_aud": 20.0, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 0.5, "duration_hours_to": 1.0, "conditions": null}]}
```

```json
{"id": "nationwide-85-north-quay", "name": "85 North Quay", "address": "85 North Quay, Brisbane QLD, Australia", "lat": -27.4697381, "lng": 153.0211675, "hours": "24/7", "height_m": 1.8, "capacity": null, "rates": [{"kind": "hourly", "label": "0.0 - 0.5 hour", "price_aud": 8.0, "online_price_aud": null, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 0.0, "duration_hours_to": 0.5, "conditions": null}, {"kind": "hourly", "label": "0.5 - 1.0 hour", "price_aud": 20.0, "online_price_aud": null, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 0.5, "duration_hours_to": 1.0, "conditions": null}, {"kind": "hourly", "label": "1.0 - 2.0 hours", "price_aud": 45.0, "online_price_aud": null, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 1.0, "duration_hours_to": 2.0, "conditions": null}]}
```

```json
{"id": "pripark-car-park-brisbane-powerhouse-new-farm", "name": "Brisbane Powerhouse New Farm Car Park", "address": "119 Lamington St, New Farm QLD", "lat": -27.468709166663842, "lng": 153.0513470253262, "hours": null, "height_m": null, "capacity": null, "rates": [{"kind": "hourly", "label": "0-30 mins", "price_aud": 0.0, "online_price_aud": null, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 0.0, "duration_hours_to": 0.5, "conditions": null}, {"kind": "hourly", "label": "30 mins - 3 hrs", "price_aud": 10.0, "online_price_aud": null, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 0.5, "duration_hours_to": 3.0, "conditions": null}, {"kind": "hourly", "label": "3-12 hrs", "price_aud": 12.0, "online_price_aud": null, "days": null, "entry_window": null, "exit_window": null, "duration_hours_from": 3.0, "duration_hours_to": 12.0, "conditions": null}]}
```
