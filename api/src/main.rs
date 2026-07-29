use brisbane_parking_api::cache::InsightCache;
use brisbane_parking_api::db::Db;
use brisbane_parking_api::insight::InsightEngine;
use brisbane_parking_api::routes::{health, list_meters, meter_detail, AppState};
use axum::{routing::get, Router};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("info".parse()?))
        .init();

    let root = project_root();
    let db_path = root.join("api").join("parking.db");
    let cache_dir = root.join("api").join(".cache");

    if !db_path.exists() {
        anyhow::bail!(
            "Database not found at {}. Run `cargo run --bin ingest` from api/ first.",
            db_path.display()
        );
    }

    let db = Arc::new(Db::open(&db_path)?);
    let cache = Arc::new(InsightCache::new(&cache_dir)?);
    let engine: AppState = Arc::new(InsightEngine::new(db, cache));

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/api/health", get(health))
        .route("/api/meters", get(list_meters))
        .route("/api/meters/{meter_no}", get(meter_detail))
        .layer(cors)
        .with_state(engine);

    let addr = SocketAddr::from(([127, 0, 0, 1], 8080));
    tracing::info!("listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

fn project_root() -> PathBuf {
    // api/src/main.rs -> api -> repo root
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    // CARGO_MANIFEST_DIR is api/
    p.pop();
    if p.join("data").exists() || p.join("brisbane-parking-meters.csv").exists() {
        return p;
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}
