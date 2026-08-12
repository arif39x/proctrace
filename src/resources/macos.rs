use crate::error::ProctraceError;
use crate::resources::now_ns;
use crate::resources::ResourceSnapshot;

pub fn snapshot() -> Result<ResourceSnapshot, ProctraceError> {
    let mut info: libc::proc_taskinfo = unsafe { std::mem::zeroed() };
    let ret = unsafe {
        // SAFETY: `info` is a writable buffer of the exact size proc_pidinfo
        // expects; the call fills it with the current process's task info.
        libc::proc_pidinfo(
            libc::getpid(),
            libc::PROC_PIDTASKINFO,
            0,
            (&mut info as *mut libc::proc_taskinfo).cast::<libc::c_void>(),
            std::mem::size_of::<libc::proc_taskinfo>() as i32,
        )
    };
    if ret <= 0 {
        return Err(ProctraceError::MacosSyscall {
            call: "PROC_PIDTASKINFO",
            source: std::io::Error::last_os_error(),
        });
    }

    let size = unsafe {
        // SAFETY: a null buffer with zero length is the documented way to
        // query the fd table size; proc_pidinfo does not write in that case.
        libc::proc_pidinfo(
            libc::getpid(),
            libc::PROC_PIDLISTFDS,
            0,
            std::ptr::null_mut(),
            0,
        )
    };
    let fd_count = if size > 0 {
        size as u32 / std::mem::size_of::<libc::proc_fdinfo>() as u32
    } else {
        0
    };

    Ok(ResourceSnapshot {
        rss_bytes: info.pti_resident_size,
        vms_bytes: info.pti_virtual_size,
        open_fds: fd_count,
        timestamp_ns: now_ns(),
    })
}

pub fn list_fd_paths() -> Result<Vec<String>, ProctraceError> {
    let mut paths = Vec::new();
    for fd in 0..4096 {
        let mut buf = vec![0u8; libc::PATH_MAX as usize];
        let ret = unsafe {
            // SAFETY: `buf` is a writable buffer of PATH_MAX bytes, which is
            // exactly what F_GETPATH writes; fcntl fails harmlessly on closed fds.
            libc::fcntl(fd, libc::F_GETPATH, buf.as_mut_ptr())
        };
        if ret == 0 {
            let len = buf.iter().position(|&b| b == 0).unwrap_or(buf.len());
            buf.truncate(len);
            paths.push(String::from_utf8_lossy(&buf).into_owned());
        }
    }
    paths.sort();
    Ok(paths)
}
