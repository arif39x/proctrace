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
#[pyfunction]
pub fn register_signal_pipe(signal_num: i32) -> PyResult<(i32, i32)> {
    // Create a non-blocking pipe with O_CLOEXEC so child processes don't inherit it
    let mut fds = [0i32; 2];       //need to creatte a non-blocking pipe and with 0_CLOEXEC so child dont heritate
    let ret = unsafe {
        libc::pipe2(fds.as_mut_ptr(), libc::O_NONBLOCK | libc::O_CLOEXEC)   // fds is a valid 2-element array & pipe2 is a standard Linux syscall
    };

    if ret != 0 {
        return Err(pyo3::exceptions::PyOSError::new_err(
            format!("pipe2 failed: {}", std::io::Error::last_os_error())
        ));
    }

    let read_fd = fds[0];
    let write_fd = fds[1];

    // Store write_fd in the static so the signal handler can use it
    PIPE_WRITE_FD.store(write_fd, std::sync::atomic::Ordering::SeqCst);

    let action = libc::sigaction {                  //C handler for the given signal
        sa_sigaction: handle_signal as libc::sighandler_t,
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