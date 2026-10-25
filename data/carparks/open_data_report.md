# Open data report: Greater Brisbane off-street car parks

Generated 2026-10-25 (AEST). Raw captures are in `raw/osm/`, `raw/council/` and `raw/public/`. The scripts that rebuild the normalised files are `raw/osm/normalise_osm.py` and `scripts/build_council_and_public.py`.

## 1. OpenStreetMap: `osm.json`

- **Query:** `amenity=parking` inside bbox (-27.75,152.65,-27.0,153.35), filtered to elements where `parking` ∈ {multi-storey, underground, surface, rooftop}, **or** `fee` is present, **or** `name` is present. Output uses `out center tags`.
- **Endpoint:** overpass.kumi.systems. **OSM base timestamp: 2026-07-15T15:22Z.** The mirror is about 3 months behind live OSM.
- **Licence:** ODbL 1.0, © OpenStreetMap contributors. Attribution is required, and derived databases are share-alike.
- **Elements:** **5,777** (263 nodes, 5,278 ways, 236 relations). All have coordinates (the centroid for ways and relations).

| parking_type | count |
|---|---|
| surface | 4,929 |
| street_side | 509 |
| multi-storey | 123 |
| underground | 100 |
| (none) | 86 |
| lane | 20 |
| rooftop | 9 |
| yes | 1 |

| fee | count |
|---|---|
| yes | **156** |
| no | 3,150 |
| null (untagged or non-yes/no) | 2,471 |

| access | count |
|---|---|
| customers | 2,444 |
| (none) | 1,427 |
| yes | 1,239 |
| private | 503 |
| permissive | 91 |
| permit | 27 |
| no | 21 |
| other | 22 |

All of these were kept, and `access` is recorded on each record.

**Attribute coverage, all 5,777:**

| attribute | count | share |
|---|---|---|
| named | 464 | 8% |
| opening_hours | 45 | 0.8% |
| capacity | 1,037 | 18% (sum 35,408 bays) |
| charge | 14 | |
| maxheight | 9 | |
| website | 11 | |
| addr:* | 68 | |
| capacity:disabled | 830 | |
| capacity:charging | 2 | |
| park_ride tagged (not "no") | 251 | |

**Paid car parks (fee=yes, 156):**

| attribute | count |
|---|---|
| named | 54 |
| hours | 20 |
| charge | 8 |
| capacity | 30 |

**Operators:**

- **All car parks:** Queensland Rail 229, 7-Eleven 13, Ipswich City Council 13, Wilson Parking 8, Secure Parking 8 (+2 tagged "Secure Parking Pty Ltd"), Brisbane City Council 8, Scentre Group 8, Brisbane Airport Corporation 8, Westfield Carindale 5.
- **Paid car parks only:** Wilson 8, Scentre Group 8, Secure 6+2, Westfield Carindale 5, First Parking 4, QUT 4+2 ("QUT"), Arts Queensland 3, Redland Hospital 3, BAC 3, BCC 2.

**Takeaway:** OSM is good for geometry and locations. It is very weak on prices: only 14 `charge` tags and 45 `opening_hours`, and operator names are inconsistent (e.g. "QUT" vs "Queensland University of Technology"). The fee flag is missing on ~43% of car parks.

## 2. Council and public sources: `council_and_public.json` (190 records)

| source | records | rates captured |
|---|---|---|
| Brisbane City Council (King George Square, Wickham Terrace) | 2 | yes: full weekday ladder, early bird, evening, weekend, PH, motorcycle |
| Translink park 'n' ride KML | 161 | no (capacity + coordinates only; fee not stated) |
| Metro South Health – PA Hospital (Wilson, First Parking) | 2 | yes |
| Children's Health Qld – QCH basement, Mater Hancock St, Mater Hill | 3 | yes (one shared Mater table) |
| Metro North – RBWH area car parks | 5 | no (page defers to operator sites) |
| Brisbane Airport (ParkShort/Long/Premium/Park&Fly/Valet/AIRPARK x2) | 7 | no (dynamic booking prices only) |
| UQ St Lucia (zoned, campus-wide) | 1 | yes (visitor zone rates) |
| QUT Gardens Point / Kelvin Grove pay-on-exit lots | 7 | no (Cloudflare; rate table not retrievable) |
| Griffith Nathan / Mt Gravatt | 2 | yes ($2/h, $6/day casual zone) |

- **Records with rates:** 10.
- **Records without coordinates:** 27 (the hospital, airport and university records, whose sources give no coordinates). Matching OSM records do exist and can be joined, e.g. Mater Hill East/West and Herston Road Car Park.

## 3. Public datasets found

| Dataset | Publisher / portal | Licence | Live? | Notes |
|---|---|---|---|---|
| `brisbane-parking-stations` (Parking — Stations) | BCC, data.brisbane.qld.gov.au (also mirrored on data.qld.gov.au) | CC BY 4.0 | **Yes, live vacant spaces** | One row: `king_george_square`, `wickham_terrace`, `uploaded_to_open_data_at`. Snapshot at 2026-10-25T03:46Z: KGS 108, WT 360 vacant. No capacity or history. |
| `railway-station-facilities` | BCC (from Queensland Rail info) | CC BY 4.0 | No | 157 stations with `cbay` (car bays), `facility_carpark`, accessible parking, lat/lng. Overlaps with the Translink KML. |
| `brisbane-parking-meters`, `parking-occupancy-forecasting*`, `disability-permit-parking-locations`, `parking-regulated-permit-parking-areas`, `cp14-city-core-frame-parking-area-boundary`, `road-restrictions` (height) | BCC | CC BY 4.0 | Forecasts only | On-street, not off-street. Height restrictions may be useful for car park entrances. |
| Translink "Park 'n' ride locations" KML (`translink.com.au/.../Park 'n' ride locations_8 (1).kml`) | Translink / TMR | **Not stated** (website content, © State of Qld). Translink GTFS is CC BY 4.0, but the KML isn't part of that feed. | No | 161 sites across SEQ with name, address, approx. spaces, point. |
| Translink GTFS / GTFS-RT | Translink | CC BY 4.0 | Realtime for vehicles only | No parking occupancy. |
| data.qld.gov.au CKAN searches (park and ride, car park, hospital parking, airport parking, translink parking) | — | — | — | No park 'n' ride, hospital, airport or university car-park dataset found. |
| Brisbane Airport, hospitals, universities | Operator websites | Website terms (no open licence) | No | Facts were transcribed. Re-check before publishing. |

**Live occupancy:** only BCC `brisbane-parking-stations` (2 car parks). There is no open live feed for park 'n' ride, the airport, hospitals or universities.

## 4. Problems and caveats

1. The Overpass mirror (kumi) data is from **2026-07-15**, which is stale. overpass-api.de returned 406 earlier.
2. OSM `fee` is missing on 2,471 car parks. Prices (`charge`) are almost absent (14), so OSM can't provide rates.
3. Query scope: 509 `street_side` and 20 `lane` elements are included because they are named or tagged with `fee`. Filter on `parking_type` if only off-street car parks are wanted.
4. Operator names in OSM aren't normalised (Secure Parking vs Secure Parking Pty Ltd, QUT vs Queensland University of Technology, Cornerstone vs Cornerstone Parking).
5. Translink KML: there's no licence statement, and fee/hours aren't given. The page says vehicles may be parked from first to last service. 25 of the 161 sites fall outside the Greater Brisbane bbox (e.g. Sunshine/Gold Coast). They are included and not filtered.
6. Council car park coordinates come from the Google Maps links on the council page (address geocodes). `parking_type` comes from the matching OSM objects.
7. QUT and Griffith sites sit behind a Cloudflare challenge. The QUT casual rate table could not be retrieved, so its rates are empty. Griffith rates came from a text extract.
8. Brisbane Airport only publishes dynamic, booking-based prices, so no static rate table was captured.
9. RBWH-area car parks: the hospital page links to operator sites (Wilson, Point, Cornerstone). Their rates weren't captured here, though the operator scrapers in `raw/` may cover them.
10. The live vacancy dataset has no capacity field. Occupancy % needs capacity from elsewhere (not published by BCC on the car park page).
11. No dedupe between `osm.json` and `council_and_public.json` has been done yet. The same car park may appear in both, e.g. KGS = osm:node/7027504446 and Wickham Tce = osm:relation/16381172.
