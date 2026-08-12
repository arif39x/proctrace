use crate::error::ProctraceError;
use crate::resources::now_ns;
use crate::resources::ResourceSnapshot;

pub fn snapshot() -> Result<ResourceSnapshot, ProctraceError> {
    let status =
        std::fs::read_to_string("/proc/self/status").map_err(|e| ProctraceError::Procfs {
            path: "/proc/self/status",
            source: e,
        })?;

    let mut rss_kb = 0u64;
    let mut vms_kb = 0u64;
    for line in status.lines() {
        if let Some(rest) = line.strip_prefix("VmRSS:") {
            rss_kb = parse_kb("VmRSS", rest)?;
        } else if let Some(rest) = line.strip_prefix("VmSize:") {
            vms_kb = parse_kb("VmSize", rest)?;
        }
        if rss_kb > 0 && vms_kb > 0 {
            break;
        }
    }

    let open_fds = std::fs::read_dir("/proc/self/fd")
        .map_err(|e| ProctraceError::Procfs {
            path: "/proc/self/fd",
            source: e,
        })?
        .flatten()
        .count() as u32;

    Ok(ResourceSnapshot {
        rss_bytes: rss_kb * 1024,
        vms_bytes: vms_kb * 1024,
        open_fds,
        timestamp_ns: now_ns(),
    })
}

pub fn list_fd_paths() -> Result<Vec<String>, ProctraceError> {
    let dir = std::fs::read_dir("/proc/self/fd").map_err(|e| ProctraceError::Procfs {
        path: "/proc/self/fd",
        source: e,
    })?;

    let mut paths = Vec::new();
    for entry in dir.flatten() {
        // Entries can vanish mid-enumeration when another thread closes an fd.
        if let Ok(target) = std::fs::read_link(entry.path()) {
            paths.push(target.to_string_lossy().into_owned());
        }
    }
    paths.sort();
    Ok(paths)
}

fn parse_kb(field: &'static str, value: &str) -> Result<u64, ProctraceError> {
    value
        .split_whitespace()
        .next()
        .ok_or_else(|| ProctraceError::StatusParse {
            field,
            detail: "empty value".into(),
        })?
        .parse::<u64>()
        .map_err(|e| ProctraceError::StatusParse {
            field,
            detail: e.to_string(),
        })
}

#[cfg(test)]
mod tests {
    use super::parse_kb;

    #[test]
    fn parses_kb_values() {
        assert_eq!(parse_kb("VmRSS", "1234 kB").unwrap(), 1234);
    }

    #[test]
    fn rejects_malformed_values() {
        assert!(parse_kb("VmRSS", "").is_err());
        assert!(parse_kb("VmRSS", "not-a-number kB").is_err());
    }
}
