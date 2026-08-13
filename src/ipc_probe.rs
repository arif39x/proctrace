use pyo3::prelude::*;
use std::collections::VecDeque;
use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::sync::Mutex;
#[pyclass]
pub struct IpcStats {
    name: String,
    latency_ring: Mutex<VecDeque<u64>>,
    ring_capacity: usize,
    total_messages: AtomicU64,
    peak_depth: AtomicU32,
}

#[pymethods]
impl IpcStats {
    #[new]
    pub fn new(name: String, ring_capacity: usize) -> Self {
        IpcStats {
            name,
            latency_ring: Mutex::new(VecDeque::with_capacity(ring_capacity)),
            ring_capacity,
            total_messages: AtomicU64::new(0),
            peak_depth: AtomicU32::new(0),
        }
    }

    pub fn record_latency_us(&self, us: u64) {
        let mut ring = self.latency_ring.lock().unwrap();
        if ring.len() >= self.ring_capacity {
            ring.pop_front();
        }
        ring.push_back(us);
        self.total_messages.fetch_add(1, Ordering::Relaxed);
    }
    pub fn record_depth(&self, depth: u32) {
        let mut current = self.peak_depth.load(Ordering::Relaxed);
        while depth > current {
            match self.peak_depth.compare_exchange_weak(
                current,
                depth,
                Ordering::SeqCst,
                Ordering::Relaxed,
            ) {
                Ok(_) => break,
                Err(actual) => current = actual,
            }
        }
    }

    pub fn avg_latency_us(&self) -> f64 {
        let ring = self.latency_ring.lock().unwrap();
        if ring.is_empty() {
            return 0.0;
        }
        ring.iter().sum::<u64>() as f64 / ring.len() as f64
    }

    pub fn p99_latency_us(&self) -> f64 {
        let ring = self.latency_ring.lock().unwrap();
        if ring.is_empty() {
            return 0.0;
        }
        let mut sorted: Vec<u64> = ring.iter().copied().collect();
        sorted.sort_unstable();
        let idx = (sorted.len() as f64 * 0.99) as usize;
        sorted[idx.min(sorted.len() - 1)] as f64
    }

    pub fn total_messages(&self) -> u64 {
        self.total_messages.load(Ordering::Relaxed)
    }

    pub fn peak_depth(&self) -> u32 {
        self.peak_depth.load(Ordering::Relaxed)
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn report(&self) -> String {
        format!(
            "{}: {} msgs | avg {:.1}µs | p99 {:.1}µs | peak depth {}",
            self.name,
            self.total_messages(),
            self.avg_latency_us(),
            self.p99_latency_us(),
            self.peak_depth(),
        )
    }
}
