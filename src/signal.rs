use pyo3::prelude::*;

static PIPE_WRITE_FD: std::sync::atomic::AtomicI32 =
    std::sync::atomic::AtomicI32::new(-1);

extern "C" fn handle_signal(_signum: libc::c_int) {      //c signale handler  
    let fd = PIPE_WRITE_FD.load(std::sync::atomic::Ordering::Relaxed);
    if fd >= 0 {
        unsafe {
            libc::write(fd, b"\x01".as_ptr() as *const libc::c_void, 1);
        }
    }
}
fn create_nonblocking_pipe() -> std::io::Result<(i32, i32)> {
    let mut fds = [0i32; 2];

    #[cfg(target_os = "linux")]
    let ret = unsafe {
        libc::pipe2(fds.as_mut_ptr(), libc::O_NONBLOCK | libc::O_CLOEXEC)
    };

    #[cfg(not(target_os = "linux"))]
    let ret = {
        // macOS/BSD lack pipe2: create a plain pipe and set the flags with fcntl
        let ret = unsafe { libc::pipe(fds.as_mut_ptr()) };
        if ret == 0 {
            for fd in &fds {
                unsafe {
                    libc::fcntl(*fd, libc::F_SETFL, libc::O_NONBLOCK);
                    libc::fcntl(*fd, libc::F_SETFD, libc::FD_CLOEXEC);
                }
            }
        }
        ret
    };

    if ret != 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok((fds[0], fds[1]))
}

#[pyfunction]
pub fn register_signal_pipe(signal_num: i32) -> PyResult<(i32, i32)> {
    let (read_fd, write_fd) = create_nonblocking_pipe().map_err(|e| {
        pyo3::exceptions::PyOSError::new_err(format!("pipe failed: {e}"))
    })?;

    // Store write_fd in the static so the signal handler can use it
    PIPE_WRITE_FD.store(write_fd, std::sync::atomic::Ordering::SeqCst);

    let action = libc::sigaction {                  //C handler for the given signal
        sa_sigaction: handle_signal as *const () as libc::sighandler_t,
        sa_mask: unsafe { std::mem::zeroed() },
        sa_flags: libc::SA_RESTART, // restart syscalls interrupted by the signal
        #[cfg(target_os = "linux")]
        sa_restorer: None,
    };

    let ret = unsafe {                                                                    
        libc::sigaction(signal_num, &action, std::ptr::null_mut()) // signal_num is a valid signal number
    };

    if ret != 0 {
        return Err(pyo3::exceptions::PyOSError::new_err(
            format!("sigaction failed: {}", std::io::Error::last_os_error())
        ));
    }

    Ok((read_fd, write_fd))
}