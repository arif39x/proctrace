use pyo3::prelude::*;

#[pyfunction]
fn probe_version() -> &'static str {
    "0.1.0"
}
#[pymodule]
fn _proctrace_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(probe_version, m)?)?;
    Ok(())
}
