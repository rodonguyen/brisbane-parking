# Secure Parking — Greater Brisbane car parks: scrape report

Generated from cached pages fetched 2026-10-25 (AEST). Parser: `data/carparks/tools/secure_parse.py` (offline, re-runnable).

## Method / endpoints

- `robots.txt` checked first (cached `raw/secure/robots.txt`): `Allow: /` but **`Disallow: /*?`** — any URL with a query string is off-limits.
- That rules out the booking widget search/JSON endpoint (`/en-au/car-parks?latitude=..&longitude=..&maxDistance=..&carparkId=..`) and any other query-string API, so no JSON API was used.
- Location list: `https://www.secureparking.com.au/en-au/sitemap.xml` (640 URLs, 385 car-park pages, **94 under `/car-parks/australia/qld/`**). Cached as `raw/secure/sitemap.xml`, URL list in `raw/secure/all_carpark_urls.txt`.
- Fetched all 94 QLD detail pages (`/en-au/car-parks/australia/qld/<slug>/`) with curl, desktop Chrome UA, 1.2 s spacing. All returned HTTP 200, with no 403s or 429s (`raw/secure/fetch_log.txt`). Raw HTML is cached as `raw/secure/page_<slug>.html`.
- Detail pages are server-rendered and contain everything parsed:
  - `data-carparkId` GUID plus car-park `data-latitude`/`data-longitude` on the search CTA, used for `id` and `lat`/`lng`.
  - Entrance/exit markers with their own coordinates, recorded in `notes`.
  - `h1` gives the name, `.car-park-detail__address` the address, and `.car-park-detail__distance` the height clearance (despite the class name).
  - `#car-park-services` list gives `features`; the Opening Hours accordion gives `hours`.
  - Rate products are in `.car-park-detail__rates-services` accordion items: title, Available/Enter/Exit, rows of `.time` + `Online $x` / `Drive-up $y`, and `data-valid-from`/`data-valid-to`/`data-is-special-day`.
  - Description text supplies monthly "from" prices and validation/free-parking offers. The Entry/Exit/Important information blocks go into `notes`.
- Filtered to the Greater Brisbane bbox: lat -27.75..-27.0, lng 152.65..153.35. 27 QLD car parks fall outside it (Gold Coast, Sunshine Coast, Cairns, Townsville, Airlie Beach).

## Counts

- QLD car-park pages in sitemap: 94 (all fetched OK)
- **Greater Brisbane car parks: 67**
- With coordinates: 67
- With at least one priced rate: 64 (with no rates listed: 502 Kingsford Smith Drive, Hamilton Car Park, 733 Ann Street, Fortitude Valley Car Park, West End Central, South Brisbane Car Park; these pages show only subscription/monthly enquiry)
- Total rate rows: 265. By kind: {'flat': 19, 'other': 33, 'night': 31, 'daily_max': 20, 'early_bird': 20, 'weekend': 23, 'hourly': 119}
- With discounts: 18

## Field fill rates (car parks)

| field | filled | % |
|---|---|---|
| id | 67/67 | 100% |
| name | 67/67 | 100% |
| address | 67/67 | 100% |
| lat | 67/67 | 100% |
| lng | 67/67 | 100% |
| url | 67/67 | 100% |
| hours | 67/67 | 100% |
| height_m | 65/67 | 97% |
| capacity | 0/67 | 0% |
| features | 67/67 | 100% |
| rates | 64/67 | 96% |
| discounts | 18/67 | 27% |
| notes | 67/67 | 100% |

## Field fill rates (rate rows)

| field | filled | % |
|---|---|---|
| price_aud | 265/265 | 100% |
| online_price_aud | 49/265 | 18% |
| days | 249/265 | 94% |
| entry_window | 249/265 | 94% |
| exit_window | 249/265 | 94% |
| duration_hours_from | 167/265 | 63% |
| duration_hours_to | 119/265 | 45% |
| conditions | 265/265 | 100% |

## Normalisation rules

- `price_aud` is the drive-up price. If a product is online/pre-book only (most Flexible Early Birds), `price_aud` = the online price and `conditions` says "Online/pre-book price only".
- `online_price_aud` is set only where the page shows an "Online $x" price.
- Tier labels like `0 Min - 30 Mins` / `2 Hours +` are parsed into `duration_hours_from`/`_to` (hours, `to` = null when open-ended).
- `kind`:
  - `daily_max`: only where the site's label says "Daily Max".
  - `flat`: "All Day"/"Daily" flat-rate products.
  - `other`: Event products and the "Monthly Parking (from)" price taken from the description (per month, new customers, minimum 3-month subscription).
  - `weekend`: includes "Sunday and Public Holidays".
  - `night`: includes "Overnight".
- `entry_window`/`exit_window`/`days` keep the site's wording, e.g. `between 06:00 AM - 09:30 AM`, `before 12:00 AM the next day`.
- `conditions` includes the product blurb plus the product validity window (`Valid <from> to <to>`, 9999 = open-ended).
- Some car parks list the same product twice with different validity windows (current price ending 2026-10-25 and new price from 2026-10-26, e.g. 201 Charlotte St EB $29.90 → $31.00). Both rows are kept; filter on the validity window in `conditions`.
- `checked_at` = UTC mtime of the cached page.

## Problems / caveats

- **Capacity is not published** on Secure Parking pages, so `capacity` is null for every car park.
- The JSON search API was not used because robots.txt disallows `/*?`. Coverage therefore depends on the sitemap. If Secure operates Brisbane car parks that aren't in the sitemap, they are missing.
- Rates are "current for today" (page disclaimer). Prices change by date, and event/special-day pricing can apply. Hourly tiers apply only within the product's day/entry/exit windows.
- The open-ended last hourly tier (e.g. `2 Hours +`) is kept as `hourly` with a note, not reclassified as `daily_max`, unless the site labels it "Daily Max".
- Discounts are thin. The site only names "Advantage Parker" (no terms on the page) and a few free-period/validation sentences (Southpoint, Stones Corner Village, The Barracks). No member/app prices are shown on the pages.
- Two car parks render height `0.00m` (730 Sandgate Rd Clayfield, 93 Logan Rd Woolloongabba). This is treated as unknown, so `height_m` = null.
- Source data quirks are kept as published, e.g. the 17 Harriett St Auchenflower address shows postcode 4870 (probably should be 4066).
- Brisbane bbox includes Caboolture, Strathpine, Ipswich and Logan/Meadowbrook.

## Sample records

### 201 Charlotte Street, Brisbane City Car Park

```json
{
  "id": "secure:1cfc5820-885b-40f0-9094-aeda009ccfe8",
  "source": "secure",
  "operator": "Secure Parking",
  "name": "201 Charlotte Street, Brisbane City Car Park",
  "address": "201 Charlotte Street, Brisbane QLD 4000",
  "lat": -27.469674,
  "lng": 153.029153,
  "url": "https://www.secureparking.com.au/en-au/car-parks/australia/qld/201-charlotte-street-brisbane-car-park/",
  "checked_at": "2026-10-25T03:44:19+00:00",
  "hours": {
    "Monday": "05:00 AM - 12:00 AM",
    "Tuesday": "05:00 AM - 12:00 AM",
    "Wednesday": "05:00 AM - 12:00 AM",
    "Thursday": "05:00 AM - 12:00 AM",
    "Friday": "05:00 AM - 12:00 AM",
    "Saturday": "07:00 AM - 12:00 AM",
    "Sunday": "07:00 AM - 12:00 AM",
    "Public Holidays": "Closed"
  },
  "height_m": 1.8,
  "capacity": null,
  "features": [
    "Monthly Parking",
    "Early Bird Parking",
    "Night Parking",
    "Weekend Parking",
    "Shopping Nearby",
    "Advantage Parker"
  ],
  "rates": [
    {
      "kind": "weekend",
      "label": "Weekend Parking - Flat Rate",
      "price_aud": 8.0,
      "online_price_aud": 9.0,
      "days": "Weekends",
      "entry_window": "after 07:00 AM",
      "exit_window": "before 12:00 AM the next day",
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Parking that makes a weekend outing stress-free; Valid 2026-10-17 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 0 Min - 30 Mins",
      "price_aud": 7.0,
      "online_price_aud": null,
      "days": "Weekdays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 12:00 AM the next day",
      "duration_hours_from": 0.0,
      "duration_hours_to": 0.5,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-10-17 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 30 Mins - 1 Hour",
      "price_aud": 14.0,
      "online_price_aud": null,
      "days": "Weekdays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 12:00 AM the next day",
      "duration_hours_from": 0.5,
      "duration_hours_to": 1.0,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-10-17 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 1 Hour - 1.5 Hours",
      "price_aud": 21.0,
      "online_price_aud": null,
      "days": "Weekdays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 12:00 AM the next day",
      "duration_hours_from": 1.0,
      "duration_hours_to": 1.5,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-10-17 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 1.5 Hours - 2 Hours",
      "price_aud": 28.0,
      "online_price_aud": null,
      "days": "Weekdays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 12:00 AM the next day",
      "duration_hours_from": 1.5,
      "duration_hours_to": 2.0,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-10-17 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 2 Hours +",
      "price_aud": 29.0,
      "online_price_aud": null,
      "days": "Weekdays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 12:00 AM the next day",
      "duration_hours_from": 2.0,
      "duration_hours_to": null,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-10-17 00:00:00 to 9999-12-31 23:59:59; Open-ended top tier within this product window"
    },
    {
      "kind": "night",
      "label": "Night Parking - Flat Rate",
      "price_aud": 10.0,
      "online_price_aud": 11.0,
      "days": "Weekdays",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 12:00 AM the next day",
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Parking that makes a night special; Valid 2026-10-17 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "early_bird",
      "label": "Flexible Early Bird Parking - Flat Rate",
      "price_aud": 29.9,
      "online_price_aud": 29.9,
      "days": "Weekdays",
      "entry_window": "between 06:00 AM - 09:30 AM",
      "exit_window": "between 09:31 AM - 10:00 PM",
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Save when in early but leave any time after morning rush; Online/pre-book price only (no drive-up price listed); Valid 2026-10-15 00:00:00 to 2026-10-25 23:59:59"
    },
    {
      "kind": "early_bird",
      "label": "Flexible Early Bird Parking - Flat Rate",
      "price_aud": 31.0,
      "online_price_aud": 31.0,
      "days": "Weekdays",
      "entry_window": "between 06:00 AM - 09:30 AM",
      "exit_window": "between 09:31 AM - 10:00 PM",
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Save when in early but leave any time after morning rush; Online/pre-book price only (no drive-up price listed); Valid 2026-10-26 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "other",
      "label": "Monthly Parking (from)",
      "price_aud": 479.0,
      "online_price_aud": null,
      "days": null,
      "entry_window": null,
      "exit_window": null,
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Per month; New customers only. Min. 3-month subscription. Terms & conditions apply"
    }
  ],
  "discounts": [
    {
      "label": "Advantage Parker",
      "details": "Car park listed as participating in Secure Parking \"Advantage Parker\" service (no details on page)."
    }
  ],
  "notes": "Entry Information: Entry via Charlotte Street.\nExit Information: Exit to Charlotte Street.\nImportant: Entry via Charlotte Street. | Exit to Charlotte Street. | Parking rates are current for today but may vary for a future date or time. Customers may be required to leave keys with valet staff upon parking. To enquire about subscription parking here please call us on 1300 048 524. Our Sales Team is available from 7:00am – 7:00pm AEST Mondays to Friday.\nEntrances/exits: Main Entry - Lane 1 - Charlotte Street (-27.46927516,153.02948848); Main Exit - Lane 1 - Charlotte Street (-27.46927516,153.02948848)"
}
```

### The Barracks, Petrie Terrace Car Park

```json
{
  "id": "secure:efc57cd5-0de5-4049-a4cf-aee400928bc8",
  "source": "secure",
  "operator": "Secure Parking",
  "name": "The Barracks, Petrie Terrace Car Park",
  "address": "61 Petrie Terrace, Brisbane QLD 4000",
  "lat": -27.465476,
  "lng": 153.013318,
  "url": "https://www.secureparking.com.au/en-au/car-parks/australia/qld/the-barracks-petrie-terrace-car-park/",
  "checked_at": "2026-10-25T03:44:46+00:00",
  "hours": {
    "Monday": "05:00 AM - 01:00 AM",
    "Tuesday": "05:00 AM - 01:00 AM",
    "Wednesday": "05:00 AM - 01:00 AM",
    "Thursday": "05:00 AM - 01:00 AM",
    "Friday": "05:00 AM - 01:00 AM",
    "Saturday": "05:00 AM - 01:00 AM",
    "Sunday": "05:00 AM - 01:00 AM",
    "Public Holidays": "05:00 AM - 01:00 AM"
  },
  "height_m": 2.2,
  "capacity": null,
  "features": [
    "Monthly Parking",
    "Event Parking",
    "Early Bird Parking",
    "Night Parking",
    "Weekend Parking",
    "Advantage Parker"
  ],
  "rates": [
    {
      "kind": "early_bird",
      "label": "Flexible Early Bird Parking - Flat Rate",
      "price_aud": 19.0,
      "online_price_aud": 19.0,
      "days": "Weekdays and Special Days",
      "entry_window": "between 05:00 AM - 09:30 AM",
      "exit_window": "between 09:31 AM - 06:00 PM",
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Save when in early but leave any time after morning rush; Online/pre-book price only (no drive-up price listed); Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 0 Hour - 2 Hours",
      "price_aud": 0.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 0.0,
      "duration_hours_to": 2.0,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 2 Hours - 2.5 Hours",
      "price_aud": 16.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 2.0,
      "duration_hours_to": 2.5,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 2.5 Hours - 3 Hours",
      "price_aud": 19.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 2.5,
      "duration_hours_to": 3.0,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 3 Hours - 3.5 Hours",
      "price_aud": 21.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 3.0,
      "duration_hours_to": 3.5,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 3.5 Hours - 4 Hours",
      "price_aud": 24.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 3.5,
      "duration_hours_to": 4.0,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 4 Hours - 4.5 Hours",
      "price_aud": 26.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 4.0,
      "duration_hours_to": 4.5,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 4.5 Hours - 5 Hours",
      "price_aud": 33.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 4.5,
      "duration_hours_to": 5.0,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 5 Hours - 5.5 Hours",
      "price_aud": 39.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 5.0,
      "duration_hours_to": 5.5,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59"
    },
    {
      "kind": "hourly",
      "label": "Hourly Parking - 5.5 Hours +",
      "price_aud": 51.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 5.5,
      "duration_hours_to": null,
      "conditions": "The best choice for short-stays or last minute parking; Valid 2026-05-02 00:00:00 to 9999-12-31 23:59:59; Open-ended top tier within this product window"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 0 Hour - 2 Hours",
      "price_aud": 0.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 0.0,
      "duration_hours_to": 2.0,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 2 Hours + (event rate applies)",
      "price_aud": 75.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 2.0,
      "duration_hours_to": null,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 2 Hours - 2.5 Hours",
      "price_aud": 16.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 2.0,
      "duration_hours_to": 2.5,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 2.5 Hours - 3 Hours",
      "price_aud": 19.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 2.5,
      "duration_hours_to": 3.0,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 3 Hours - 3.5 Hours",
      "price_aud": 21.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 3.0,
      "duration_hours_to": 3.5,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 3.5 Hours - 4 Hours",
      "price_aud": 24.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 3.5,
      "duration_hours_to": 4.0,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 4 Hours - 4.5 Hours",
      "price_aud": 26.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 4.0,
      "duration_hours_to": 4.5,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 4.5 Hours - 5 Hours",
      "price_aud": 33.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 4.5,
      "duration_hours_to": 5.0,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 5 Hours - 5.5 Hours",
      "price_aud": 39.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 5.0,
      "duration_hours_to": 5.5,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Drive-Up - 5.5 Hours +",
      "price_aud": 51.0,
      "online_price_aud": null,
      "days": "SpecialDay",
      "entry_window": "after 02:00 PM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": 5.5,
      "duration_hours_to": null,
      "conditions": "Pricing applies when there is an event due to high demand.; Valid 2026-09-10 00:00:00 to 2026-11-05 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Event Parking Pre-Paid - Event rate",
      "price_aud": 75.0,
      "online_price_aud": 75.0,
      "days": "SpecialDay",
      "entry_window": "after 09:30 AM",
      "exit_window": "before 01:00 AM the next day",
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Pricing applies when there is an event due to high demand; Online/pre-book price only (no drive-up price listed); Valid 2026-10-25 00:00:00 to 9999-12-31 23:59:59; Special-day product"
    },
    {
      "kind": "other",
      "label": "Monthly Parking (from)",
      "price_aud": 299.0,
      "online_price_aud": null,
      "days": null,
      "entry_window": null,
      "exit_window": null,
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "Per month; New customers only. Min. 3-month subscription. Terms & conditions apply"
    }
  ],
  "discounts": [
    {
      "label": "First 2 hours parking is FREE for Shoppers",
      "details": "First 2 hours parking is FREE for Shoppers."
    },
    {
      "label": "PALACE CINEMA PARKING - pull paper ticket on entry and validate at cinema before",
      "details": "PALACE CINEMA PARKING - pull paper ticket on entry and validate at cinema before leaving to get discounted rate."
    },
    {
      "label": "Advantage Parker",
      "details": "Car park listed as participating in Secure Parking \"Advantage Parker\" service (no details on page)."
    }
  ],
  "notes": "Entry Information: Entry via Petrie Terrace.\nExit Information: Exit to Petrie Terrace.\nImportant: Entry via Petrie Terrace. | Exit to Petrie Terrace. | Parking rates are current for today but may vary. 2 hours free parking valid only once in a 24-hour period. Disability access - restricted lift and ramp access at this car park. Event pricing applies at this car park when there is an event at Suncorp Stadium due to high demand. Please review before confirming. To enquire about subscription parking here please call us on 1300 048 524. Our Sales Team is available from 7:00am – 7:00pm AEST Mondays to Friday.\nEntrances/exits: Main Entry - Lane 1 - Petrie Terrace (-27.46509773,153.0134918); Main Exit - Lane 1 - Petrie Terrace (-27.46509773,153.0134918)"
}
```

### 13 Wharf Street, Ipswich Car Park

```json
{
  "id": "secure:a9e89552-9559-4f13-a223-b413001340db",
  "source": "secure",
  "operator": "Secure Parking",
  "name": "13 Wharf Street, Ipswich Car Park",
  "address": "13 Wharf Street, Ipswich QLD 4305",
  "lat": -27.613276,
  "lng": 152.762349,
  "url": "https://www.secureparking.com.au/en-au/car-parks/australia/qld/13-wharf-street-ipswich-car-park/",
  "checked_at": "2026-10-25T03:46:45+00:00",
  "hours": {
    "Monday": "24 Hours",
    "Tuesday": "24 Hours",
    "Wednesday": "24 Hours",
    "Thursday": "24 Hours",
    "Friday": "24 Hours",
    "Saturday": "24 Hours",
    "Sunday": "24 Hours",
    "Public Holidays": "24 Hours"
  },
  "height_m": 3.0,
  "capacity": null,
  "features": [
    "Monthly Parking",
    "24 hours",
    "Disability Access",
    "Night Parking",
    "Weekend Parking",
    "Motorcycle Parking",
    "Shopping Nearby",
    "4WD Parking"
  ],
  "rates": [
    {
      "kind": "flat",
      "label": "All Day Parking - Flat Rate",
      "price_aud": 6.0,
      "online_price_aud": null,
      "days": "Weekdays, Weekends and Public Holidays",
      "entry_window": "after 05:00 AM",
      "exit_window": "before 05:00 AM the next day",
      "duration_hours_from": null,
      "duration_hours_to": null,
      "conditions": "A smarter way to park all day; Valid 2026-06-03 00:00:00 to 9999-12-31 23:59:59"
    }
  ],
  "discounts": [],
  "notes": "Entry Information: Entry via Wharf Street.\nExit Information: Exit to Wharf Street.\nImportant: Entry via Wharf Street. | Exit to Wharf Street. | Parking rates are current for today but may vary for a future date or time. To enquire about subscription parking here please call us on 1300 048 524. Our Sales Team is available from 7:00am – 7:00pm AEST Mondays to Friday.\nEntrances/exits: Main Entry - Lane 1 - Wharf Street (-27.613276,152.762349)"
}
```
