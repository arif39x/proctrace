use pyo3::prelude::*;

mod error;
mod resources;
mod sampler;

use resources::ResourceSnapshot;
use sampler::BackgroundSampler;

#[pyfunction]
fn probe_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pyfunction]
fn snapshot_resources() -> PyResult<ResourceSnapshot> {
    resources::snapshot().map_err(Into::into)
}

#[pyfunction]
fn list_open_fds() -> PyResult<Vec<String>> {
    resources::list_fd_paths().map_err(Into::into)
}

#[pymodule]
fn _proctrace_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(probe_version, m)?)?;
    m.add_function(wrap_pyfunction!(snapshot_resources, m)?)?;
    m.add_function(wrap_pyfunction!(list_open_fds, m)?)?;
    m.add_class::<ResourceSnapshot>()?;
    m.add_class::<BackgroundSampler>()?;
    Ok(())
}
