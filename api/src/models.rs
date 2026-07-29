use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeterSummary {
    pub meter_no: String,
    pub street: String,
    pub suburb: String,
    pub loc_desc: String,
    pub latitude: f64,
    pub longitude: f64,
    pub mobile_zone: String,
    pub veh_bays: i32,
    pub max_stay_hrs: String,
    pub operational_day: String,
    pub operational_time: String,
    pub tar_rate_weekday: String,
    pub tar_rate_ah_we: String,
    pub category: String,
    pub chance_free: Option<f64>,
    pub occupancy_pred: Option<f64>,
    pub lookup_method: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HourPoint {
    pub hour: i32,
    pub occupancy_pred: f64,
    pub chance_free: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextPoint {
    pub label: String,
    pub occupancy_pred: f64,
    pub chance_free: f64,
    pub sample_count: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NearbyMeter {
    pub meter_no: String,
    pub street: String,
    pub suburb: String,
    pub distance_m: f64,
    pub chance_free: Option<f64>,
    pub occupancy_pred: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeterInsight {
    pub meter: MeterSummary,
    pub brisbane_now: String,
    pub next_hour: i32,
    pub target_date: String,
    pub day_class: String,
    pub season: String,
    pub is_holiday: bool,
    pub next_hour_chance_free: Option<f64>,
    pub next_hour_occupancy: Option<f64>,
    pub next_hour_label: String,
    pub lookup_method: String,
    pub today_series: Vec<HourPoint>,
    pub typical_series: Vec<HourPoint>,
    pub context_comparison: Vec<ContextPoint>,
    pub nearby: Vec<NearbyMeter>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MapResponse {
    pub brisbane_now: String,
    pub next_hour: i32,
    pub target_date: String,
    pub meters: Vec<MeterSummary>,
}

pub fn chance_free(occupancy_pred: f64) -> f64 {
    ((5.0 - occupancy_pred) / 5.0).clamp(0.0, 1.0)
}

pub fn chance_label(chance: Option<f64>) -> String {
    match chance {
        Some(c) if c >= 0.6 => "Likely".into(),
        Some(c) if c >= 0.35 => "Mixed".into(),
        Some(_) => "Unlikely".into(),
        None => "Unknown".into(),
    }
}
