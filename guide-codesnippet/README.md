# guide-codesnippet

Runnable code examples for proctrace.  
Read **[GUIDE.md](../GUIDE.md)** first for the full architecture and usage docs.

---

| # | File | Topic | Run |
|---|---|---|---|
| 1 | [`01_basic_watch.py`](./01_basic_watch.py) | Minimal `watch()` context manager | `python 01_basic_watch.py` |
| 2 | [`02_selective_tracking.py`](./02_selective_tracking.py) | Enable only specific metrics | `python 02_selective_tracking.py` |
| 3 | [`03_probe_decorator.py`](./03_probe_decorator.py) | `@probe` on sync and async functions | `python 03_probe_decorator.py` |
| 4 | [`04_json_export.py`](./04_json_export.py) | Serialise `ResourceDelta` to JSON / dict | `python 04_json_export.py` |
| 5 | [`05_fd_leak_detection.py`](./05_fd_leak_detection.py) | Detect file descriptor leaks | `python 05_fd_leak_detection.py` |
| 6 | [`06_ipc_tracing.py`](./06_ipc_tracing.py) | Trace queues, pipes, and sockets | `python 06_ipc_tracing.py` |
| 7 | [`07_signal_dump.py`](./07_signal_dump.py) | On-demand thread + asyncio dump via signal | `python 07_signal_dump.py` |
| 8 | [`08_cli_usage.sh`](./08_cli_usage.sh) | CLI `run`, `watch`, `dump` commands | `bash 08_cli_usage.sh` |

---

## Prerequisites

```bash
pip install proctrace
# or from source:
pip install maturin && maturin develop --release
```

Python >= 3.10 · Linux or macOS
