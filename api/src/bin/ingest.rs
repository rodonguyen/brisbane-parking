use brisbane_parking_api::db::{ingest_meters, ingest_occupancy, Db};
use std::path::{Path, PathBuf};
use std::time::Instant;

fn main() -> anyhow::Result<()> {
    let root = find_root();
    let db_path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("parking.db");
    let data = root.join("data");

    let meters = first_existing(&[
        data.join("brisbane-parking-meters.csv"),
        root.join("brisbane-parking-meters.csv"),
    ])?;
    let occ_2026 = first_existing(&[
        data.join("parking-occupancy-forecasting.csv"),
        root.join("parking-occupancy-forecasting.csv"),
    ])?;
    let occ_2025 = first_existing(&[
        data.join("parking-occupancy-forecasting-2025.csv"),
        root.join("parking-occupancy-forecasting-2025.csv"),
    ])?;

    println!("DB: {}", db_path.display());
    println!("Meters: {}", meters.display());
    println!("Occupancy 2026: {}", occ_2026.display());
    println!("Occupancy 2025: {}", occ_2025.display());

    let db = Db::open(&db_path)?;
    db.init_schema()?;
    db.clear_data()?;

    let conn = db.connect()?;
    let t0 = Instant::now();
    let n_meters = ingest_meters(&conn, &meters)?;
    println!("Ingested {n_meters} meters in {:.1}s", t0.elapsed().as_secs_f64());

    let t1 = Instant::now();
    let n1 = ingest_occupancy(&conn, &occ_2026)?;
    println!(
        "Ingested {n1} occupancy rows (2026 file) in {:.1}s",
        t1.elapsed().as_secs_f64()
    );

    let t2 = Instant::now();
    let n2 = ingest_occupancy(&conn, &occ_2025)?;
    println!(
        "Ingested {n2} occupancy rows (2025 file) in {:.1}s",
        t2.elapsed().as_secs_f64()
    );

    conn.execute_batch("ANALYZE;")?;
    println!("Done. Total occupancy inserts attempted: {}", n1 + n2);
    Ok(())
}

fn find_root() -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.pop();
    if p.join("data").exists() || p.join("brisbane-parking-meters.csv").exists() {
        p
    } else {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
    }
}

fn first_existing(paths: &[PathBuf]) -> anyhow::Result<PathBuf> {
    for p in paths {
        if p.exists() {
            return Ok(p.clone());
        }
    }
    anyhow::bail!(
        "none of these paths exist: {:?}",
        paths.iter().map(|p| p.display().to_string()).collect::<Vec<_>>()
    );
}

#[allow(dead_code)]
fn _path_hint(p: &Path) -> String {
    p.display().to_string()
}
