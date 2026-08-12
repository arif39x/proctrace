use crate::error::ProctraceError;
use pyo3::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};

#[cfg(target_os = "linux")]
mod linux;

#[cfg(target_os = "macos")]
mod macos;

#[cfg(target_os = "linux")]
use linux as backend;

#[cfg(target_os = "macos")]
use macos as backend;

/// Byte-level resource usage of this process at a single instant.
/// Timestamps are Unix nanoseconds so callers can compute deltas.
#[pyclass(skip_from_py_object)]
#[derive(Debug)]
pub struct ResourceSnapshot {
    #[pyo3(get)]
    pub rss_bytes: u64,

    #[pyo3(get)]
    pub vms_bytes: u64,

    #[pyo3(get)]
    pub open_fds: u32,

    #[pyo3(get)]
    pub timestamp_ns: u64,
}

#[pymethods]
impl ResourceSnapshot {
    pub fn rss_mb(&self) -> f64 {
        self.rss_bytes as f64 / (1024.0 * 1024.0)
    }

    pub fn vms_mb(&self) -> f64 {
        self.vms_bytes as f64 / (1024.0 * 1024.0)
    }

    pub fn __repr__(&self) -> String {
        format!(
            "ResourceSnapshot(rss={:.1}MB, vms={:.1}MB, fds={})",
            self.rss_mb(),
            self.vms_mb(),
            self.open_fds
        )
    }
}

fn now_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64
}

#[cfg(any(target_os = "linux", target_os = "macos"))]
pub fn snapshot() -> Result<ResourceSnapshot, ProctraceError> {
    backend::snapshot()
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
pub fn snapshot() -> Result<ResourceSnapshot, ProctraceError> {
    Err(ProctraceError::UnsupportedPlatform)
}

#[cfg(any(target_os = "linux", target_os = "macos"))]
pub fn list_fd_paths() -> Result<Vec<String>, ProctraceError> {
    backend::list_fd_paths()
}

#[cfg(not(any(target_os = "linux", target_os = "macos")))]
pub fn list_fd_paths() -> Result<Vec<String>, ProctraceError> {
    Err(ProctraceError::UnsupportedPlatform)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn converts_bytes_to_mb() {
        let snap = ResourceSnapshot {
            rss_bytes: 2 * 1024 * 1024,
            vms_bytes: 1024 * 1024,
            open_fds: 0,
            timestamp_ns: 0,
        };
        assert_eq!(snap.rss_mb(), 2.0);
        assert_eq!(snap.vms_mb(), 1.0);
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn snapshot_reports_live_process_state() {
        let snap = snapshot().unwrap();
        assert!(snap.open_fds > 0);
        assert!(snap.rss_bytes > 0);
        assert!(snap.vms_bytes >= snap.rss_bytes);
    }
}
