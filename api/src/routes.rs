use crate::insight::InsightEngine;
use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;
use std::sync::Arc;

pub type AppState = Arc<InsightEngine>;

pub async fn health() -> impl IntoResponse {
    Json(json!({ "ok": true, "service": "brisbane-parking-api" }))
}

pub async fn list_meters(State(engine): State<AppState>) -> impl IntoResponse {
    match tokio::task::spawn_blocking(move || engine.map_meters()).await {
        Ok(Ok(resp)) => (StatusCode::OK, Json(resp)).into_response(),
        Ok(Err(e)) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}

pub async fn meter_detail(
    State(engine): State<AppState>,
    Path(meter_no): Path<String>,
) -> impl IntoResponse {
    match tokio::task::spawn_blocking(move || engine.meter_insight(&meter_no)).await {
        Ok(Ok(Some(insight))) => (StatusCode::OK, Json(insight)).into_response(),
        Ok(Ok(None)) => (
            StatusCode::NOT_FOUND,
            Json(json!({ "error": "meter not found" })),
        )
            .into_response(),
        Ok(Err(e)) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}
