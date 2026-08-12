//! Background memory sampler.
//!
//! Spawns a native OS thread (not a Python thread) that polls RSS every
//! interval_ms milliseconds and stores the peak in an AtomicU64.
//!
//! SAFETY: the Rust thread never touches a Python object; it only reads
//! /proc/self/status and writes to an AtomicU64, so it can run without the GIL.
use crate::resources::snapshot;
use pyo3::prelude::*;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

#[pyclass]
pub struct BackgroundSampler {
    stop_flag: Arc<AtomicBool>, // Main thread sets  true so sampler thread exits
    peak_rss: Arc<AtomicU64>,   // Peak RSS seen since start() Read by main thread after stop()
    handle: Option<thread::JoinHandle<()>>, // Handle to the spawned thread None if not started yet
}

#[pymethods]
impl BackgroundSampler {
    #[new]
    pub fn new() -> Self {
        BackgroundSampler {
            stop_flag: Arc::new(AtomicBool::new(false)),
            peak_rss: Arc::new(AtomicU64::new(0)),
            handle: None,
        }
    }

    pub fn start(&mut self, interval_ms: u64) {
        // 50ms to 500ms (High to low overhead)
        self.stop_flag.store(false, Ordering::SeqCst); // reseting for state reuse
        self.peak_rss.store(0, Ordering::SeqCst);

        let stop = Arc::clone(&self.stop_flag);
        let peak = Arc::clone(&self.peak_rss);
        let interval = Duration::from_millis(interval_ms);

        self.handle = Some(thread::spawn(move || {
            while !stop.load(Ordering::Relaxed) {
                if let Ok(snap) = snapshot() {
                    let mut current = peak.load(Ordering::Relaxed);
                    while snap.rss_bytes > current {
                        match peak.compare_exchange_weak(
                            current,
                            snap.rss_bytes,
                            Ordering::SeqCst,
                            Ordering::Relaxed,
                        ) {
                            Ok(_) => break,
                            Err(actual) => current = actual,
                        }
                    }
                }
                thread::sleep(interval);
            }
        }));
    }

    pub fn stop(&mut self) -> u64 {
        //sampler will stop and return peak rss
        self.stop_flag.store(true, Ordering::SeqCst);
        if let Some(handle) = self.handle.take() {
            //thread joining for peak rss written purpose
            let _ = handle.join();
        }
        self.peak_rss.load(Ordering::SeqCst)
    }
}
