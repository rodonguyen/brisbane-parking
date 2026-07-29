use anyhow::Result;
use moka::sync::Cache;
use serde::de::DeserializeOwned;
use serde::Serialize;
use std::fs;
use std::hash::Hash;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

const TTL: Duration = Duration::from_secs(24 * 60 * 60);

pub struct InsightCache {
    memory: Cache<String, String>,
    dir: PathBuf,
}

impl InsightCache {
    pub fn new(dir: impl AsRef<Path>) -> Result<Self> {
        let dir = dir.as_ref().to_path_buf();
        fs::create_dir_all(&dir)?;
        let memory = Cache::builder().time_to_live(TTL).max_capacity(10_000).build();
        Ok(Self { memory, dir })
    }

    pub fn get_json<T: DeserializeOwned>(&self, key: &str) -> Option<T> {
        if let Some(raw) = self.memory.get(key) {
            if let Ok(v) = serde_json::from_str(&raw) {
                return Some(v);
            }
        }
        let path = self.path_for(key);
        if !path.exists() {
            return None;
        }
        if !is_fresh(&path) {
            let _ = fs::remove_file(&path);
            return None;
        }
        let raw = fs::read_to_string(&path).ok()?;
        let v: T = serde_json::from_str(&raw).ok()?;
        self.memory.insert(key.to_string(), raw);
        Some(v)
    }

    pub fn set_json<T: Serialize>(&self, key: &str, value: &T) -> Result<()> {
        let raw = serde_json::to_string(value)?;
        self.memory.insert(key.to_string(), raw.clone());
        let path = self.path_for(key);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, raw)?;
        Ok(())
    }
}

fn path_safe(key: &str) -> String {
    key.chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '-' || c == '_' { c } else { '_' })
        .collect()
}

impl InsightCache {
    fn path_for(&self, key: &str) -> PathBuf {
        self.dir.join(format!("{}.json", path_safe(key)))
    }
}

fn is_fresh(path: &Path) -> bool {
    let Ok(meta) = fs::metadata(path) else {
        return false;
    };
    let Ok(modified) = meta.modified() else {
        return false;
    };
    SystemTime::now()
        .duration_since(modified)
        .map(|d| d < TTL)
        .unwrap_or(false)
}

pub fn cache_key(parts: &[&str]) -> String {
    parts.join(":")
}

// Silence unused Hash import warning if any
#[allow(dead_code)]
fn _hash_bound<T: Hash>(_: T) {}
