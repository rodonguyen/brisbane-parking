use crate::holidays::{day_class, season};
use anyhow::{Context, Result};
use chrono::NaiveDate;
use rusqlite::{params, Connection, OptionalExtension};
use std::path::{Path, PathBuf};

pub struct Db {
    path: PathBuf,
}

impl Db {
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let conn = Connection::open(&path)?;
        conn.execute_batch(
            "
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            PRAGMA temp_store = MEMORY;
            ",
        )?;
        Ok(Self { path })
    }

    pub fn connect(&self) -> Result<Connection> {
        let conn = Connection::open(&self.path)?;
        conn.execute_batch("PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;")?;
        Ok(conn)
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn init_schema(&self) -> Result<()> {
        let conn = self.connect()?;
        conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS meters (
                meter_no TEXT PRIMARY KEY,
                category TEXT,
                street TEXT,
                suburb TEXT,
                max_stay_hrs TEXT,
                restrictions TEXT,
                operational_day TEXT,
                operational_time TEXT,
                tar_zone TEXT,
                tar_rate_weekday TEXT,
                tar_rate_ah_we TEXT,
                loc_desc TEXT,
                veh_bays INTEGER,
                mc_bays INTEGER,
                longitude REAL,
                latitude REAL,
                mobile_zone TEXT,
                max_cap_chg TEXT
            );

            CREATE TABLE IF NOT EXISTS occupancy (
                mobile_zone TEXT NOT NULL,
                date TEXT NOT NULL,
                hour INTEGER NOT NULL,
                occupancy_pred REAL NOT NULL,
                day_class TEXT NOT NULL,
                season TEXT NOT NULL,
                PRIMARY KEY (mobile_zone, date, hour)
            );

            CREATE INDEX IF NOT EXISTS idx_occ_zone_hour_ctx
                ON occupancy (mobile_zone, hour, day_class, season);
            CREATE INDEX IF NOT EXISTS idx_occ_zone_date
                ON occupancy (mobile_zone, date);
            CREATE INDEX IF NOT EXISTS idx_meters_zone
                ON meters (mobile_zone);
            CREATE INDEX IF NOT EXISTS idx_meters_geo
                ON meters (latitude, longitude);
            ",
        )?;
        Ok(())
    }

    pub fn clear_data(&self) -> Result<()> {
        let conn = self.connect()?;
        conn.execute_batch("DELETE FROM occupancy; DELETE FROM meters;")?;
        Ok(())
    }
}

pub fn ingest_meters(conn: &Connection, csv_path: &Path) -> Result<usize> {
    let mut rdr = csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(csv_path)
        .with_context(|| format!("open meters csv {}", csv_path.display()))?;

    let tx = conn.unchecked_transaction()?;
    {
        let mut stmt = tx.prepare(
            "INSERT OR REPLACE INTO meters (
                meter_no, category, street, suburb, max_stay_hrs, restrictions,
                operational_day, operational_time, tar_zone, tar_rate_weekday,
                tar_rate_ah_we, loc_desc, veh_bays, mc_bays, longitude, latitude,
                mobile_zone, max_cap_chg
            ) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18)",
        )?;

        let mut count = 0usize;
        for result in rdr.deserialize() {
            let row: MeterCsv = result?;
            let meter_no = row.meter_no.trim_start_matches('\u{feff}').to_string();
            let veh_bays = row
                .veh_bays_int
                .or_else(|| parse_i32(&row.veh_bays))
                .unwrap_or(0);
            let mc_bays = parse_i32(&row.mc_bays).unwrap_or(0);
            let longitude: f64 = row.longitude.parse().unwrap_or(0.0);
            let latitude: f64 = row.latitude.parse().unwrap_or(0.0);
            if longitude == 0.0 || latitude == 0.0 {
                continue;
            }
            stmt.execute(params![
                meter_no,
                row.category,
                row.street,
                row.suburb,
                row.max_stay_hrs,
                row.restrictions,
                row.operational_day,
                row.operational_time,
                row.tar_zone,
                row.tar_rate_weekday,
                row.tar_rate_ah_we,
                row.loc_desc,
                veh_bays,
                mc_bays,
                longitude,
                latitude,
                row.mobile_zone,
                row.max_cap_chg,
            ])?;
            count += 1;
        }
        drop(stmt);
        tx.commit()?;
        Ok(count)
    }
}

pub fn ingest_occupancy(conn: &Connection, csv_path: &Path) -> Result<usize> {
    let mut rdr = csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(csv_path)
        .with_context(|| format!("open occupancy csv {}", csv_path.display()))?;

    let tx = conn.unchecked_transaction()?;
    {
        let mut stmt = tx.prepare(
            "INSERT OR IGNORE INTO occupancy (
                mobile_zone, date, hour, occupancy_pred, day_class, season
            ) VALUES (?1,?2,?3,?4,?5,?6)",
        )?;

        let mut count = 0usize;
        for result in rdr.deserialize() {
            let row: OccCsv = result?;
            let zone = row.mobile_zone.trim_start_matches('\u{feff}').to_string();
            let hour = row.hour as i32;
            let date = NaiveDate::parse_from_str(&row.date, "%Y-%m-%d")
                .with_context(|| format!("bad date {}", row.date))?;
            let dc = day_class(date);
            let s = season(date);
            stmt.execute(params![
                zone,
                row.date,
                hour,
                row.occupancy_pred,
                dc,
                s
            ])?;
            count += 1;
            if count % 500_000 == 0 {
                eprintln!("  … ingested {count} occupancy rows from {}", csv_path.display());
            }
        }
        drop(stmt);
        tx.commit()?;
        Ok(count)
    }
}

pub fn get_occupancy(
    conn: &Connection,
    zone: &str,
    date: &str,
    hour: i32,
) -> Result<Option<f64>> {
    let val: Option<f64> = conn
        .query_row(
            "SELECT occupancy_pred FROM occupancy
             WHERE mobile_zone = ?1 AND date = ?2 AND hour = ?3",
            params![zone, date, hour],
            |r| r.get(0),
        )
        .optional()?;
    Ok(val)
}

pub fn avg_occupancy_context(
    conn: &Connection,
    zone: &str,
    hour: i32,
    day_class: &str,
    season: &str,
) -> Result<Option<(f64, i64)>> {
    let row: Option<(f64, i64)> = conn
        .query_row(
            "SELECT AVG(occupancy_pred), COUNT(*) FROM occupancy
             WHERE mobile_zone = ?1 AND hour = ?2 AND day_class = ?3 AND season = ?4",
            params![zone, hour, day_class, season],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    Ok(row.filter(|(_, n)| *n > 0))
}

pub fn avg_occupancy_hour(conn: &Connection, zone: &str, hour: i32) -> Result<Option<(f64, i64)>> {
    let row: Option<(f64, i64)> = conn
        .query_row(
            "SELECT AVG(occupancy_pred), COUNT(*) FROM occupancy
             WHERE mobile_zone = ?1 AND hour = ?2",
            params![zone, hour],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    Ok(row.filter(|(_, n)| *n > 0))
}

pub fn series_for_date(
    conn: &Connection,
    zone: &str,
    date: &str,
) -> Result<Vec<(i32, f64)>> {
    let mut stmt = conn.prepare(
        "SELECT hour, occupancy_pred FROM occupancy
         WHERE mobile_zone = ?1 AND date = ?2
         ORDER BY hour",
    )?;
    let rows = stmt
        .query_map(params![zone, date], |r| Ok((r.get(0)?, r.get(1)?)))?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(rows)
}

pub fn typical_series(
    conn: &Connection,
    zone: &str,
    day_class: &str,
    season: &str,
) -> Result<Vec<(i32, f64, i64)>> {
    let mut stmt = conn.prepare(
        "SELECT hour, AVG(occupancy_pred), COUNT(*) FROM occupancy
         WHERE mobile_zone = ?1 AND day_class = ?2 AND season = ?3
         GROUP BY hour
         ORDER BY hour",
    )?;
    let rows = stmt
        .query_map(params![zone, day_class, season], |r| {
            Ok((r.get(0)?, r.get(1)?, r.get(2)?))
        })?
        .collect::<Result<Vec<_>, _>>()?;
    Ok(rows)
}

#[derive(Debug, serde::Deserialize)]
struct MeterCsv {
    #[serde(rename = "METER_NO", alias = "\u{feff}METER_NO")]
    meter_no: String,
    #[serde(rename = "CATEGORY")]
    category: String,
    #[serde(rename = "STREET")]
    street: String,
    #[serde(rename = "SUBURB")]
    suburb: String,
    #[serde(rename = "MAX_STAY_HRS")]
    max_stay_hrs: String,
    #[serde(rename = "RESTRICTIONS")]
    restrictions: String,
    #[serde(rename = "OPERATIONAL_DAY")]
    operational_day: String,
    #[serde(rename = "OPERATIONAL_TIME")]
    operational_time: String,
    #[serde(rename = "TAR_ZONE")]
    tar_zone: String,
    #[serde(rename = "TAR_RATE_WEEKDAY")]
    tar_rate_weekday: String,
    #[serde(rename = "TAR_RATE_AH_WE")]
    tar_rate_ah_we: String,
    #[serde(rename = "LOC_DESC")]
    loc_desc: String,
    #[serde(rename = "VEH_BAYS")]
    veh_bays: String,
    #[serde(rename = "MC_BAYS")]
    mc_bays: String,
    #[serde(rename = "LONGITUDE")]
    longitude: String,
    #[serde(rename = "LATITUDE")]
    latitude: String,
    #[serde(rename = "MOBILE_ZONE")]
    mobile_zone: String,
    #[serde(rename = "MAX_CAP_CHG")]
    max_cap_chg: String,
    #[serde(rename = "VEH_BAYS_INT")]
    veh_bays_int: Option<i32>,
}

#[derive(Debug, serde::Deserialize)]
struct OccCsv {
    #[serde(rename = "MOBILE_ZONE", alias = "\u{feff}MOBILE_ZONE")]
    mobile_zone: String,
    #[serde(rename = "DATE")]
    date: String,
    #[serde(rename = "HOUR")]
    hour: f64,
    #[serde(rename = "OCCUPANCY_PRED")]
    occupancy_pred: f64,
}

fn parse_i32(s: &str) -> Option<i32> {
    let t = s.trim();
    if t.is_empty() {
        return None;
    }
    t.parse().ok().or_else(|| t.parse::<f64>().ok().map(|v| v as i32))
}
