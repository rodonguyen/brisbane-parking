use crate::cache::{cache_key, InsightCache};
use crate::db::{
    avg_occupancy_context, avg_occupancy_hour, get_occupancy, series_for_date, typical_series, Db,
};
use crate::holidays::{day_class, is_qld_holiday, season};
use crate::models::{
    chance_free, chance_label, ContextPoint, HourPoint, MapResponse, MeterInsight, MeterSummary,
    NearbyMeter,
};
use anyhow::Result;
use chrono::Timelike;
use chrono_tz::Australia::Brisbane;
use rusqlite::{params, Connection, OptionalExtension};
use std::sync::Arc;

pub struct InsightEngine {
    pub db: Arc<Db>,
    pub cache: Arc<InsightCache>,
}

impl InsightEngine {
    pub fn new(db: Arc<Db>, cache: Arc<InsightCache>) -> Self {
        Self { db, cache }
    }

    pub fn brisbane_clock(&self) -> (String, String, i32, String, String, bool) {
        let now = chrono::Utc::now().with_timezone(&Brisbane);
        let next_hour = ((now.hour() + 1) % 24) as i32;
        let mut target = now.date_naive();
        if now.hour() == 23 {
            target = target.succ_opt().unwrap_or(target);
        }
        let date_str = target.format("%Y-%m-%d").to_string();
        let dc = day_class(target).to_string();
        let s = season(target).to_string();
        let holiday = is_qld_holiday(target);
        let now_str = now.format("%Y-%m-%d %H:%M %Z").to_string();
        (now_str, date_str, next_hour, dc, s, holiday)
    }

    pub fn map_meters(&self) -> Result<MapResponse> {
        let (now_str, date_str, next_hour, dc, season_s, _) = self.brisbane_clock();
        let key = cache_key(&["map", "next-hour", &date_str, &next_hour.to_string()]);
        if let Some(cached) = self.cache.get_json::<MapResponse>(&key) {
            return Ok(cached);
        }

        let conn = self.db.connect()?;
        let meters = load_all_meters(&conn)?;
        let mut out = Vec::with_capacity(meters.len());
        for mut m in meters {
            let (occ, method) =
                resolve_occupancy(&conn, &m.mobile_zone, &date_str, next_hour, &dc, &season_s)?;
            m.occupancy_pred = occ;
            m.chance_free = occ.map(chance_free);
            m.lookup_method = Some(method);
            out.push(m);
        }

        let resp = MapResponse {
            brisbane_now: now_str,
            next_hour,
            target_date: date_str,
            meters: out,
        };
        let _ = self.cache.set_json(&key, &resp);
        Ok(resp)
    }

    pub fn meter_insight(&self, meter_no: &str) -> Result<Option<MeterInsight>> {
        let (now_str, date_str, next_hour, dc, season_s, holiday) = self.brisbane_clock();
        let key = cache_key(&["insight", meter_no, &date_str, &next_hour.to_string()]);
        if let Some(cached) = self.cache.get_json::<MeterInsight>(&key) {
            return Ok(Some(cached));
        }

        let conn = self.db.connect()?;
        let Some(mut meter) = load_meter(&conn, meter_no)? else {
            return Ok(None);
        };

        let (occ, method) =
            resolve_occupancy(&conn, &meter.mobile_zone, &date_str, next_hour, &dc, &season_s)?;
        meter.occupancy_pred = occ;
        meter.chance_free = occ.map(chance_free);
        meter.lookup_method = Some(method.clone());

        let today_raw = series_for_date(&conn, &meter.mobile_zone, &date_str)?;
        let today_series: Vec<HourPoint> = today_raw
            .into_iter()
            .map(|(h, o)| HourPoint {
                hour: h,
                occupancy_pred: o,
                chance_free: chance_free(o),
            })
            .collect();

        let typical_raw = typical_series(&conn, &meter.mobile_zone, &dc, &season_s)?;
        let typical_series: Vec<HourPoint> = typical_raw
            .into_iter()
            .map(|(h, o, _)| HourPoint {
                hour: h,
                occupancy_pred: o,
                chance_free: chance_free(o),
            })
            .collect();

        let context_comparison =
            build_context_comparison(&conn, &meter.mobile_zone, next_hour, &dc, &season_s)?;

        let nearby = find_nearby(
            &conn,
            &meter.meter_no,
            meter.latitude,
            meter.longitude,
            &date_str,
            next_hour,
            &dc,
            &season_s,
            meter.chance_free,
        )?;

        let insight = MeterInsight {
            next_hour_chance_free: meter.chance_free,
            next_hour_occupancy: occ,
            next_hour_label: chance_label(meter.chance_free),
            lookup_method: method,
            meter,
            brisbane_now: now_str,
            next_hour,
            target_date: date_str,
            day_class: dc,
            season: season_s,
            is_holiday: holiday,
            today_series,
            typical_series,
            context_comparison,
            nearby,
        };
        let _ = self.cache.set_json(&key, &insight);
        Ok(Some(insight))
    }
}

fn resolve_occupancy(
    conn: &Connection,
    zone: &str,
    date: &str,
    hour: i32,
    day_class: &str,
    season: &str,
) -> Result<(Option<f64>, String)> {
    if let Some(v) = get_occupancy(conn, zone, date, hour)? {
        return Ok((Some(v), "exact".into()));
    }
    if let Some((avg, n)) = avg_occupancy_context(conn, zone, hour, day_class, season)? {
        return Ok((Some(avg), format!("analog:{day_class}:{season}:n={n}")));
    }
    if let Some((avg, n)) = avg_occupancy_hour(conn, zone, hour)? {
        return Ok((Some(avg), format!("zone-hour:n={n}")));
    }
    Ok((None, "unavailable".into()))
}

fn build_context_comparison(
    conn: &Connection,
    zone: &str,
    hour: i32,
    current_dc: &str,
    current_season: &str,
) -> Result<Vec<ContextPoint>> {
    let mut out = Vec::new();
    for (label, dc, s) in [
        ("This context", current_dc, current_season),
        ("Weekdays (same season)", "weekday", current_season),
        ("Weekends (same season)", "weekend", current_season),
        ("Holidays (same season)", "holiday", current_season),
    ] {
        if let Some((avg, n)) = avg_occupancy_context(conn, zone, hour, dc, s)? {
            out.push(ContextPoint {
                label: label.into(),
                occupancy_pred: avg,
                chance_free: chance_free(avg),
                sample_count: n,
            });
        }
    }
    Ok(out)
}

fn find_nearby(
    conn: &Connection,
    meter_no: &str,
    lat: f64,
    lon: f64,
    date: &str,
    hour: i32,
    day_class: &str,
    season: &str,
    self_chance: Option<f64>,
) -> Result<Vec<NearbyMeter>> {
    let d = 0.004;
    let mut stmt = conn.prepare(
        "SELECT meter_no, street, suburb, latitude, longitude, mobile_zone
         FROM meters
         WHERE meter_no != ?1
           AND latitude BETWEEN ?2 AND ?3
           AND longitude BETWEEN ?4 AND ?5",
    )?;
    let candidates: Vec<(String, String, String, f64, f64, String)> = stmt
        .query_map(params![meter_no, lat - d, lat + d, lon - d, lon + d], |r| {
            Ok((
                r.get(0)?,
                r.get(1)?,
                r.get(2)?,
                r.get(3)?,
                r.get(4)?,
                r.get(5)?,
            ))
        })?
        .collect::<Result<Vec<_>, _>>()?;

    let mut scored = Vec::new();
    for (mno, street, suburb, mlat, mlon, zone) in candidates {
        let dist = haversine_m(lat, lon, mlat, mlon);
        if dist > 300.0 {
            continue;
        }
        let (occ, _) = resolve_occupancy(conn, &zone, date, hour, day_class, season)?;
        let chance = occ.map(chance_free);
        if let (Some(sc), Some(ch)) = (self_chance, chance) {
            if ch <= sc {
                continue;
            }
        }
        scored.push(NearbyMeter {
            meter_no: mno,
            street,
            suburb,
            distance_m: dist.round(),
            chance_free: chance,
            occupancy_pred: occ,
        });
    }
    scored.sort_by(|a, b| {
        b.chance_free
            .partial_cmp(&a.chance_free)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| {
                a.distance_m
                    .partial_cmp(&b.distance_m)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
    });
    scored.truncate(3);
    Ok(scored)
}

fn haversine_m(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let r = 6_371_000.0;
    let to_rad = |d: f64| d.to_radians();
    let dlat = to_rad(lat2 - lat1);
    let dlon = to_rad(lon2 - lon1);
    let a = (dlat / 2.0).sin().powi(2)
        + to_rad(lat1).cos() * to_rad(lat2).cos() * (dlon / 2.0).sin().powi(2);
    2.0 * r * a.sqrt().asin()
}

fn load_all_meters(conn: &Connection) -> Result<Vec<MeterSummary>> {
    let mut stmt = conn.prepare(
        "SELECT meter_no, street, suburb, loc_desc, latitude, longitude, mobile_zone,
                veh_bays, max_stay_hrs, operational_day, operational_time,
                tar_rate_weekday, tar_rate_ah_we, category
         FROM meters",
    )?;
    let rows = stmt
        .query_map([], |r| {
            Ok(MeterSummary {
                meter_no: r.get(0)?,
                street: r.get(1)?,
                suburb: r.get(2)?,
                loc_desc: r.get(3)?,
                latitude: r.get(4)?,
                longitude: r.get(5)?,
                mobile_zone: r.get(6)?,
                veh_bays: r.get(7)?,
                max_stay_hrs: r.get(8)?,
                operational_day: r.get(9)?,
                operational_time: r.get(10)?,
                tar_rate_weekday: r.get(11)?,
                tar_rate_ah_we: r.get(12)?,
                category: r.get(13)?,
                chance_free: None,
                occupancy_pred: None,
                lookup_method: None,
            })
        })?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(rows)
}

fn load_meter(conn: &Connection, meter_no: &str) -> Result<Option<MeterSummary>> {
    let row = conn
        .query_row(
            "SELECT meter_no, street, suburb, loc_desc, latitude, longitude, mobile_zone,
                    veh_bays, max_stay_hrs, operational_day, operational_time,
                    tar_rate_weekday, tar_rate_ah_we, category
             FROM meters WHERE meter_no = ?1",
            params![meter_no],
            |r| {
                Ok(MeterSummary {
                    meter_no: r.get(0)?,
                    street: r.get(1)?,
                    suburb: r.get(2)?,
                    loc_desc: r.get(3)?,
                    latitude: r.get(4)?,
                    longitude: r.get(5)?,
                    mobile_zone: r.get(6)?,
                    veh_bays: r.get(7)?,
                    max_stay_hrs: r.get(8)?,
                    operational_day: r.get(9)?,
                    operational_time: r.get(10)?,
                    tar_rate_weekday: r.get(11)?,
                    tar_rate_ah_we: r.get(12)?,
                    category: r.get(13)?,
                    chance_free: None,
                    occupancy_pred: None,
                    lookup_method: None,
                })
            },
        )
        .optional()?;
    Ok(row)
}
