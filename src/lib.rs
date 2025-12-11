use pyo3::prelude::*;

mod csv_handler;

#[pymodule]
fn rustlibs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(csv_handler::get_csv_files_from_folder, m)?)?;
    Ok(())
}
