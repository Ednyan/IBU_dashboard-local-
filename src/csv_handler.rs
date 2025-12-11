use dotenvy::dotenv;
use glob::glob;
use pyo3::prelude::*;
use std::env;
use std::path::Path;

#[pyfunction]
pub fn get_csv_files_from_folder() -> Vec<String> {
    dotenv().ok();

    let data_folder = match env::var("DATA_FOLDER") {
        Ok(v) => v,
        Err(_) => return vec![],
    };

    if !Path::new(&data_folder).exists() {
        return vec![];
    };
    let pattern = format!("{}/sheepit_team_points_*.csv", data_folder);

    let paths = match glob(&pattern) {
        Ok(p) => p,
        Err(_) => return Vec::new(),
    };

    let mut files: Vec<String> = paths
        .filter_map(|entry| entry.ok())
        .map(|p| p.to_string_lossy().into_owned())
        .collect();

    // Sort reverse (most recent filename first)
    files.sort_by(|a, b| b.cmp(a));

    files
}
