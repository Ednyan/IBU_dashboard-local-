use pyo3::prelude::*;

#[pyfunction]
fn rs_hello() -> String {
    "Hello from Rust!".to_string()
}

#[pymodule]
fn rustlibs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rs_hello, m)?)?;
    Ok(())
}
