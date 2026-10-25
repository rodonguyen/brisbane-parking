# Greater Brisbane shopping-centre parking – scrape report

Checked: 2026-10-25 (AEST). Output: `data/carparks/malls.json` (59 centres). Raw cache: `data/carparks/raw/malls/` (HTML/PDF + `.meta.json` per fetch). Scripts: `data/carparks/scripts/fetch_malls.py` (robots.txt check, ≥1.1 s between requests, Chrome UA, caching), `malls_to_text.py`; target lists `mall_targets*.json`.

## Method
- Discovery: web search per centre/owner (Westfield/Scentre, Vicinity, QIC, Mirvac, HomeCo, Dexus, Stockland etc.) inside bbox lat −27.75..−27.0, lng 152.65..153.35.
- Fetch: official centre parking / getting-here page; where the centre delegates to a car-park operator page (Secure Parking, First Parking, Point Parking, Uptown Parking) that page was used and is flagged in `operator`/`notes`.
- Extraction: manual reading of the page text; every value is from the page. **lat/lng are null everywhere** – no page stated coordinates (no geocoding done, per rules).
- `free_period_hours` is only set when the page states a time-limited free period; centres advertising unlimited "free parking" have `free_period_hours: null` plus a `flat` rate of $0 and feature `free_parking`.

## Fill rates

| field | filled | % |
|---|---|---|
| with_any_rates | 39 | 66% |
| with_paid_rates | 19 | 32% |
| parking_page | 48 | 81% |
| address | 53 | 90% |
| lat/lng | 0 | 0% |
| hours | 14 | 24% |
| height_m | 16 | 27% |
| capacity | 26 | 44% |
| free_period_hours | 13 | 22% |
| discounts | 18 | 31% |
| ev_charging | 10 | 17% |
| free_parking_feature | 18 | 31% |

## Centres

| id | name | operator | parking info on page | free period (h) | paid tiers | daily max | source |
|---|---|---|---|---|---|---|---|
| albany-creek-village | Albany Creek Village | Albany Creek Village | no/minimal | – | – | – | [link](https://albanycreekvillage.com.au/about) |
| arndale-springwood | Arndale Springwood | Consolidated Properties | yes | – | – | – | [link](https://arndale.com.au/location/) |
| aspley-hypermarket | Aspley Hypermarket | Aspley Hypermarket | yes | – | – | – | [link](https://www.aspleyhypermarket.com.au/centre-info/getting-here) |
| beenleigh-marketplace | Beenleigh Marketplace | Beenleigh Marketplace | no/minimal | – | – | – | [link](https://www.beenleighmarketplace.com.au/) |
| booval-fair | Booval Fair | Booval Fair | yes | – | – | – | [link](https://boovalfair.com.au/centre-info/getting-here) |
| bracken-ridge-plaza | Bracken Ridge Plaza | Bracken Ridge Plaza | yes | – | – | – | [link](https://brackenridgeplaza.com.au/centre-information) |
| brassall | Brassall Shopping Centre | Brassall Shopping Centre | yes | – | – | – | [link](https://brassallsc.com.au/parking/) |
| bribie-island-central | Bribie Island Central | Bribie Island Central | no/minimal | – | – | – | [link](https://www.bribieislandcentral.com.au/find-us) |
| brisbane-arcade | Brisbane Arcade | Brisbane Arcade | no/minimal | – | – | – | [link](https://brisbanearcade.com.au/visit-brisbane-arcade/) |
| brookside | Brookside Shopping Centre | Brookside | no/minimal | – | – | – | [link](https://www.brookside.com.au/) |
| caboolture-square | Caboolture Square | Caboolture Square | yes | – | – | – | [link](https://caboolturesquare.com.au/getting-here) |
| calamvale-central | Calamvale Central | Calamvale Central | yes | – | – | – | [link](https://calamvalecentral.com.au/centre-info/getting-here) |
| cannon-hill-kmart-plaza | Cannon Hill Kmart Plaza | Cannon Hill Kmart Plaza | yes | – | – | – | [link](https://cannonhillkmartplaza.com.au/centre-info/getting-here) |
| capalaba-central | Capalaba Central | Capalaba Central | yes | – | – | – | [link](https://capalabacentral.com.au/centre-info/getting-here) |
| capalaba-park | Capalaba Park Shopping Centre | Capalaba Park (managed by Retail First) | yes | – | – | – | [link](https://www.capalabapark.com.au/centre-info/getting-here) |
| carseldine-central | Carseldine Central | Carseldine Central | yes | – | – | – | [link](https://www.carseldinecentral.com.au/our-centre) |
| cleveland-central | Cleveland Central | Cleveland Central (Haben) | yes | 4 | – | – | [link](https://www.clevelandcentral.com.au/location-parking) |
| coorparoo-square | Coorparoo Square | Coorparoo Square | yes | 3 | 8 | $17 | [link](https://coorparoosquare.com.au/centre-information) |
| dfo-brisbane | DFO Brisbane (Skygate) | Vicinity Centres (car parks managed by Brisbane Airport Corporation) | yes | – | 8 | $41 | [link](https://www.brisbane.dfo.com.au/directions/parking) |
| dfo-jindalee | DFO Jindalee | DFO Jindalee | no/minimal | – | – | – | [link](https://dfojindalee.com.au/contact) |
| emporium | Emporium Fortitude Valley – 1024 Ann Street car park | Emporium precinct (car park by Secure Parking) | yes | – | 2 | – | [link](https://www.secureparking.com.au/en-au/car-parks/australia/qld/1024-ann-street-fortitude-valley-car-park) |
| gasworks-plaza | Gasworks Plaza | Gasworks Plaza (car park by Point Parking) | yes | 2 | 7 | $65 | [link](https://pointparking.com.au/locations/gasworks-plaza/) |
| grand-plaza | Grand Plaza Browns Plains | Vicinity Centres (car park monitored by Secure Parking / TMS) | yes | 4 | 1 | – | [link](https://www.grandplaza.com.au/directions/parking) |
| homeco-lutwyche | HomeCo. Lutwyche (formerly Lutwyche City) | HomeCo (HMC Capital) | yes | 3 | 9 | $40 | [link](https://home-co.com.au/lutwyche/centre-info/directions-parking) |
| homeco-victoria-point | HomeCo. Victoria Point | HomeCo (HMC Capital) | yes | – | – | – | [link](https://home-co.com.au/victoria-point/centre-info/directions-parking) |
| hyperdome | Hyperdome (Loganholme) | QIC | yes | – | – | – | [link](https://hyperdomeshopping.com.au/getting-here/) |
| inala-plaza | Inala Plaza | Inala Plaza | no/minimal | – | – | – | [link](https://inalaplaza.com.au/about/find-us/) |
| indooroopilly | Indooroopilly Shopping Centre | Dexus (car park operated by Point Parking) | yes | 3 | 20 | $30 | [link](https://www.indooroopillyshopping.com.au/visit/parking.html) |
| kallangur-fair | Ganellen Kallangur Fair | Ganellen | yes | – | – | – | [link](https://www.kallangurfair.com.au/parking) |
| kenmore-village | Kenmore Village | Kenmore Village | yes | – | – | – | [link](https://kenmorevillage.com.au/facilities/) |
| logan-central-plaza | Logan Central Plaza | Logan Central Plaza | no/minimal | – | – | – | [link](https://www.logancentralplaza.com.au/) |
| macarthur-central | MacArthur Central | MacArthur Central (car park by Secure Parking) | yes | – | 7 | $29 | [link](https://www.macarthurcentral.com.au/visit/parking) |
| market-square-sunnybank | Market Square Sunnybank | Market Square (car park by Secure Parking) | no/minimal | – | – | – | [link](https://www.secureparking.com.au/en-au/car-parks/australia/qld/market-square-shopping-centre-sunnybank-car-park) |
| mcwhirters | McWhirters (Fortitude Valley) – Secure Parking McWhirters | McWhirters Marketplace (car park by Secure Parking) | yes | – | 6 | $13 | [link](https://www.secureparking.com.au/en-au/car-parks/australia/qld/mcwhirters-fortitude-valley-car-park) |
| morayfield | Morayfield Shopping Centre | Morayfield Shopping Centre | yes | – | – | – | [link](http://morayfieldshoppingcentre.com.au/visit/getting-here) |
| mt-ommaney | Mt Ommaney Centre | Mt Ommaney Centre | no/minimal | – | – | – | [link](https://mtommaneycentre.com.au/centre-info/getting-here) |
| myer-centre | Uptown Brisbane (formerly The Myer Centre) – Uptown Parking | Uptown Brisbane (formerly The Myer Centre) | yes | – | 12 | $70 | [link](https://www.uptownbrisbane.com.au/parking) |
| orion-springfield | Orion Springfield Central | Mirvac | yes | – | – | – | [link](https://www.orionspringfieldcentral.com.au/visit/parking) |
| peninsula-fair | Peninsula Fair | Peninsula Fair (managed by Retail First) | yes | – | – | – | [link](https://www.penfair.com.au/centre-info/getting-here/) |
| queensplaza | QueensPlaza | Vicinity Centres | yes | – | 12 | $80 | [link](https://www.queensplaza.com.au/car-park-rates) |
| redbank-plaza | Redbank Plaza | Redbank Plaza | yes | – | – | – | [link](https://redbankplaza.com.au/centre-info/getting-here) |
| riverlink | Ipswich Riverlink Shopping Centre | Riverlink | yes | – | – | – | [link](https://www.riverlink.net.au/visit/getting-here/) |
| sbh-shoppingtown | Sunnybank Hills Shoppingtown | Sunnybank Hills Shoppingtown | yes | – | – | – | [link](https://www.sbhshoppingtown.com.au/centre-info/getting-here) |
| skygate | Skygate (Skygate Centre / precinct) | Brisbane Airport Corporation | yes | 3 | 1 | – | [link](https://www.skygate.com.au/parking) |
| southpoint-south-bank | Southpoint South Bank | Southpoint (car park by Secure Parking) | yes | – | – | – | [link](https://southpointsouthbank.com.au/parking/) |
| stafford-city | Stafford City | Stafford City | yes | – | – | – | [link](https://www.staffordcity.com.au/centre-info/getting-here/) |
| strathpine-centre | Strathpine Centre | Strathpine Centre (formerly Westfield Strathpine) | yes | – | – | – | [link](https://www.strathpinecentre.com.au/centre-information/getting-here) |
| sunnybank-plaza | Sunnybank Plaza | Sunnybank Plaza | yes | – | – | – | [link](https://sunnybankplaza.com.au/centre-info/getting-here) |
| toowong-village | Toowong Village | Toowong Village (car park by Nationwide Parking) | yes | 3 | 10 | $49 | [link](https://www.toowongvillage.com.au/centre-information/parking) |
| valley-metro | Valley Metro Fortitude Valley | Valley Metro (car park by First Parking) | yes | – | 6 | $61 | [link](https://www.firstparking.com.au/locations/valley-metro) |
| victoria-point-lakeside | Victoria Point Lakeside | Victoria Point Lakeside (managed by All Commercial Properties Qld) | no/minimal | – | – | – | [link](https://victoriapointlakeside.com.au/about) |
| westfield-carindale | Westfield Carindale | Scentre Group | yes | 3 | 21 | $36 | [link](https://www.westfield.com.au/carindale/parking) |
| westfield-chermside | Westfield Chermside | Scentre Group | yes | 2 | 17 | $36 | [link](https://www.westfield.com.au/chermside/parking) |
| westfield-mt-gravatt | Westfield Mt Gravatt (Garden City) | Scentre Group | yes | 3 | 20 | $36 | [link](https://www.westfield.com.au/mtgravatt/parking) |
| westfield-north-lakes | Westfield North Lakes | Scentre Group | yes | 3 | 11 | $36 | [link](https://www.westfield.com.au/northlakes/parking) |
| westpoint-browns-plains | Westpoint Browns Plains | Westpoint | yes | 2 | – | – | [link](https://www.westpointbrownsplains.com.au/centre-info/) |
| wintergarden | Wintergarden – Secure Parking Wintergarden Brisbane City | Wintergarden (car park operated by Secure Parking) | yes | – | 6 | $26 | [link](https://www.secureparking.com.au/en-au/car-parks/australia/qld/wintergarden-brisbane-city-car-park/) |
| wynnum-plaza | Wynnum Plaza | Wynnum Plaza | yes | – | – | – | [link](https://www.wynnumplaza.com/centre-info) |
| yamanto-central | Yamanto Central | Yamanto Central | yes | – | – | – | [link](https://yamantocentral.com.au/centre-information) |

## Not included / problems

- **Toombul Shopping Centre** – closed since the 2022 flood; site sold by Mirvac to Irvine (2025), redevelopment application lodged Oct 2026 (news via search). Not in JSON.
- **Victoria Point Shopping Centre** (victoriapointshoppingcentre.com.au) – HTTP 403 to normal request; not circumvented. HomeCo. Victoria Point and Victoria Point Lakeside are included.
- **Newmarket Village** – HTTP 503 on two attempts (plain fetch and real browser). Not included.
- **Stockland Cleveland** – Stockland URL 404; Cleveland Central (90-91 Middle St) appears to be the same site, included.
- **Market Square Sunnybank** – Secure Parking car-park URL no longer renders a car park (redirects to search); included with no rates.
- **Robots.txt disallowed**: Toowong Village conditions-of-entry PDF (webflow CDN), QueensPlaza car-park T&C PDF (storyblok). Skipped.
- `hyperdomeshopping.qicre.com` (from search) didn't resolve; the main Hyperdome site was used.
- Pages with **no parking text** in static HTML: Brookside, Mt Ommaney, Logan Central Plaza, Inala Plaza, Bribie Island Central (JS finder only), Beenleigh Marketplace (homepage capacity only).
- Many suburban centres advertise free parking but give **no time limit/fees**: Capalaba Park, Capalaba Central, Calamvale, Stafford City, Booval Fair, Cannon Hill, Kenmore, Carseldine, Wynnum Plaza, Yamanto have `rates: []` (unknown), not $0.
- **Secure Parking pages** give rates "current for today but may vary" and sometimes list two early-bird prices (both kept; second in `conditions`). Their EV icon is a generic search filter, so not treated as confirmed EV.
- **DFO Brisbane** shows two multi-deck tables; the newer one is used (the other says "correct as of May 2021").
- **Grand Plaza** "rate" of $77 is the breach notice for staying over the 4-hour free limit (`kind: other`), not a parking fee.
- **Westfield Chermside** says spend/cinema validation is **not available**. All four Westfields: member (app) 4 h free, ticketless LPR, $36 daily max/overnight. Evening free after 5:30pm is members-only at Chermside/Carindale/Mt Gravatt and open to everyone at North Lakes.
- Westfield Coomera is outside the bbox (Gold Coast), so excluded.
- The Myer Centre is now **Uptown** (themyercentre.com.au redirects to uptownbrisbane.com.au).
- Strathpine is no longer Westfield ("Strathpine Centre", free parking).

## Sample records

### westfield-chermside
```json
{
 "id": "westfield-chermside",
 "source": "mall",
 "operator": "Scentre Group",
 "name": "Westfield Chermside",
 "address": "Cnr Gympie & Hamilton Rds, Chermside QLD 4032",
 "lat": null,
 "lng": null,
 "url": "https://www.westfield.com.au/chermside/parking",
 "checked_at": "2026-10-25",
 "hours": null,
 "height_m": 2.0,
 "capacity": null,
 "features": [
  "ticketless_lpr",
  "no_entry_boom_gate",
  "valet",
  "staff_parking",
  "pram_parking",
  "mobility_permit_free",
  "pay_in_app"
 ],
 "free_period_hours": 2,
 "rates": [
  {
   "kind": "hourly",
   "label": "Standard 0-2h",
   "price_aud": 0,
   "online_price_aud": null,
   "days": "Mon-Sun",
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 0,
   "duration_hours_to": 2,
   "conditions": null
  },
  {
   "kind": "hourly",
   "label": "Standard 2-2.5h",
   "price_aud": 4,
   "online_price_aud": null,
   "days": "Mon-Sun",
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 2,
   "duration_hours_to": 2.5,
   "conditions": null
  },
  {
   "kind": "hourly",
   "label": "Standard 2.5-3h",
   "price_aud": 6,
   "online_price_aud": null,
   "days": "Mon-Sun",
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 2.5,
   "duration_hours_to": 3,
   "conditions": null
  },
  "…"
 ],
 "discounts": [
  {
   "label": "Westfield membership (app)",
   "details": "4 hours free instead of 2; free entry after 5:30pm exiting before 1am. Add number plate in Westfield app."
  },
  {
   "label": "Cinema/spend validation",
   "details": "Not available at Westfield Chermside (stated on page)."
  },
  {
   "label": "Mobility permit",
   "details": "Free parking on presentation of valid permit at Concierge (Level 1 near Target)."
  },
  {
   "label": "Game day",
   "details": "$10 all-day flat rate with valid event tickets, entry before 5:30pm."
  },
  {
   "label": "Valet",
   "details": "Full valet Mon-Fri $12, Sat-Sun $15; every 6th visit free (loyalty)."
  },
  {
   "label": "Staff",
   "details": "Dedicated staff parking areas for retailers; contact Concierge."
  }
 ],
 "notes": "Ticketless number-plate recognition, no entry boom gate. Re-entry more than 45 min after previous exit on same day earns another free period. Vehicles left >24h may be towed. Height limits per car park: White/Lime/Pink/Blue 2.2m, Grey/Red 2.3m, Orange 2.0m, Gold 3.6m (height_m = lowest). EV: ChargePoint chargers removed Feb 2024; replacement pending. Payment at pay stations (cas
```

### indooroopilly
```json
{
 "id": "indooroopilly",
 "source": "mall",
 "operator": "Dexus (car park operated by Point Parking)",
 "name": "Indooroopilly Shopping Centre",
 "address": "322 Moggill Rd, Indooroopilly QLD 4068",
 "lat": null,
 "lng": null,
 "url": "https://www.indooroopillyshopping.com.au/visit/parking.html",
 "checked_at": "2026-10-25",
 "hours": null,
 "height_m": null,
 "capacity": null,
 "features": [
  "ticketless_lpr",
  "valet",
  "staff_parking",
  "monthly_parking",
  "motorcycle_free",
  "ev_charging"
 ],
 "free_period_hours": 3,
 "rates": [
  {
   "kind": "hourly",
   "label": "Standard 0-3h",
   "price_aud": 0,
   "online_price_aud": null,
   "days": "Mon-Sun",
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 0,
   "duration_hours_to": 3,
   "conditions": "Free 3h once per parking day (4am-3:59am); multiple visits accumulate"
  },
  {
   "kind": "hourly",
   "label": "Standard 3-3.5h",
   "price_aud": 4,
   "online_price_aud": null,
   "days": "Mon-Sun",
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 3,
   "duration_hours_to": 3.5,
   "conditions": "Free 3h once per parking day (4am-3:59am); multiple visits accumulate"
  },
  {
   "kind": "hourly",
   "label": "Standard 3.5-4h",
   "price_aud": 5,
   "online_price_aud": null,
   "days": "Mon-Sun",
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 3.5,
   "duration_hours_to": 4,
   "conditions": "Free 3h once per parking day (4am-3:59am); multiple visits accumulate"
  },
  "…"
 ],
 "discounts": [
  {
   "label": "Spend $200",
   "details": "Free parking when spending $200+ same day; present receipts + rego at Concierge (Level 2 Information Desk) during opening hours."
  },
  {
   "label": "Cinema / restaurant validation",
   "details": "4 hours free with validation voucher from Event Cinemas, Cutler's Arms, Betty's Burgers, Bobby Q, Grill'd, Yum Cha Cuisine; scan at pay machine. Standard rates from 5th hour starting $7."
  },
  {
   "label": "Parking Account (online registration)",
   "details": "4 hours free per day plus automatic payment."
  },
  {
   "label": "Disability permit",
   "details": "Free parking account after permit verification."
  },
  {
   "label": "Motorcycle",
   "details": "Free in designated motorcycle bays."
  },
  {
   "label": "Staff",
   "details": "$4 daily flat rate in designated staff areas."
  },
  {
   "label": "Valet",
   "details": "$5 Thu & Fri; $10 weekends and public holidays (in addition to pa
```

### grand-plaza
```json
{
 "id": "grand-plaza",
 "source": "mall",
 "operator": "Vicinity Centres (car park monitored by Secure Parking / TMS)",
 "name": "Grand Plaza Browns Plains",
 "address": "27-49 Browns Plains Rd, Browns Plains QLD 4118",
 "lat": null,
 "lng": null,
 "url": "https://www.grandplaza.com.au/directions/parking",
 "checked_at": "2026-10-25",
 "hours": null,
 "height_m": null,
 "capacity": 2500,
 "features": [
  "time_limited",
  "no_boom_gates",
  "ev_charging",
  "accessible_bays",
  "parents_with_prams_bays",
  "undercover_partial"
 ],
 "free_period_hours": 4,
 "rates": [
  {
   "kind": "flat",
   "label": "Free parking up to 4 hours",
   "price_aud": 0,
   "online_price_aud": null,
   "days": null,
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 0,
   "duration_hours_to": 4,
   "conditions": "Customers of the centre; no on-site charges under 4h"
  },
  {
   "kind": "other",
   "label": "Breach notice for exceeding 4-hour free period",
   "price_aud": 77,
   "online_price_aud": null,
   "days": null,
   "entry_window": null,
   "exit_window": null,
   "duration_hours_from": 4,
   "duration_hours_to": null,
   "conditions": "Issued by TMS; appeal at Customer Service Desk with proof of shopping >4h"
  }
 ],
 "discounts": [
  {
   "label": "Proof of purchase",
   "details": "Customers with proof of purchase who were in centre longer than 4h can appeal breach notices."
  }
 ],
 "notes": "Page says 2,667 spaces on directions page and \"over 2,500\" on parking page (capacity uses 2,500 conservative). EV chargers (DC fast + AC) in Red car park above Kmart, pay-per-kWh via Exploren / Chargefox apps. Limited undercover parking in Orange car park ground level. Also sourced from: https://www.grandplaza.com.au/directions"
}
```
