# Changelog

## [0.1.0] — 2026-08-12

### Added
- `proctrace.watch()` context manager: monitor memory, fd, thread, child process deltas
- `@proctrace.probe()` decorator: wraps sync and async functions
- `proctrace.install_signal_handler()`: SIGUSR1-triggered thread + asyncio dump
- `proctrace.trace_ipc(queue)`: latency and depth tracking for queues
- `proctrace.trace_pipe(r, w)`: latency tracking for pipe pairs
- `proctrace.trace_socket(sock)`: send latency + recv buffer utilization for sockets
- `proctrace.ipc_report()`: human-readable IPC channel summary
- `ProctraceLogger`: JSONL structured logging for ResourceDelta events
- `pytest-proctrace` plugin: per-test resource tracking via `--proctrace`
- `proctrace` CLI: `run`, `dump`, `watch` subcommands
- Linux backend: `/proc/self/status`, `/proc/self/fd`
- macOS backend: `proc_pidinfo(PROC_PIDTASKINFO)`, `fcntl(F_GETPATH)`
- Background Rust sampler thread for peak RSS tracking
- Zero runtime Python dependencies

### Platform support
- Linux: ✓ (primary development platform)
- macOS: ✓ (tested on arm64 and x86_64)
- Windows: ✗ (no `/proc`, no `POSIX signals`)
