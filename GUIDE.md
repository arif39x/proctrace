# proctrace — Developer Guide

> Non-invasive process and OS-state introspection for Python.  
> Diagnose memory leaks, FD leaks, race conditions, and IPC bottlenecks with a single import.

---

## Table of Contents

1. [Architecture](#architecture)
2. [How to Use proctrace](#how-to-use-proctrace)
   - [Installation](#installation)
   - [Context Manager (watch)](#context-manager-watch)
   - [Decorator (@probe)](#decorator-probe)
   - [IPC Tracing](#ipc-tracing)
   - [On-demand Stack Dumps](#on-demand-stack-dumps)
   - [CLI](#cli)
3. [API Reference](#api-reference)
4. [Code Snippets](#code-snippets)

---

## Architecture

proctrace is a **two-layer library**: a compiled Rust extension provides the low-level OS sampling, and a pure-Python layer offers the ergonomic API surface developers actually interact with.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Python Code                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │  import proctrace
┌─────────────────────────▼───────────────────────────────────────┐
│                  Python Public API Layer                        │
│                                                                 │
│   watch() / ResourceWatcher       @probe decorator              │
│   trace_ipc / trace_pipe / trace_socket / ipc_report            │
│   install_signal_handler()                                      │
│                                                                 │
│   proctrace/__init__.py                                         │
│   proctrace/watch.py          proctrace/decorators.py           │
│   proctrace/ipc.py            proctrace/snapshot.py             │
│   proctrace/_types.py         (ResourceDelta dataclass)         │
└─────────────────────────┬───────────────────────────────────────┘
                          │  PyO3 FFI boundary
┌─────────────────────────▼───────────────────────────────────────┐
│                  Rust Core Extension                            │
│              (_proctrace_core.cpython-*.so)                     │
│                                                                 │
│   resources.rs    — snapshot_resources(), list_open_fds()       │
│   sampler.rs      — BackgroundSampler (peak RSS thread)         │
│   ipc_probe.rs    — IpcStats, SocketStats                       │
│   signal.rs       — register_signal_pipe()                      │
│   lib.rs          — PyO3 module root                            │
└─────────────────────────────────────────────────────────────────┘
                          │
                     Linux /proc
                     (macOS sysctl)
```

### Component Breakdown

| Component | File | Responsibility |
|---|---|---|
| `ResourceWatcher` | `watch.py` | Context manager; snapshots resources before/after a block; runs `BackgroundSampler` in the background |
| `BackgroundSampler` | `sampler.rs` | Rust thread that polls RSS on a configurable interval to capture the **peak** |
| `ResourceDelta` | `_types.py` | Pure-Python dataclass holding all measurements; serialises to/from dict/JSON |
| `@probe` decorator | `decorators.py` | Wraps sync and async functions with a `ResourceWatcher`; optionally stores result on `fn.last_probe_result` |
| IPC tracers | `ipc.py` | Thin wrappers around `queue.Queue`, OS pipes, and `socket` that record latency and throughput via `IpcStats`/`SocketStats` |
| Signal handler | `snapshot.py` | Installs a self-pipe trick via `register_signal_pipe()` (Rust); a daemon thread reads it and dumps all Python thread stacks + asyncio tasks |
| CLI | `cli.py` | `proctrace run / watch / dump` subcommands |
| Rust extension | `src/` | Compiled `.so`; exposes `snapshot_resources`, `list_open_fds`, `BackgroundSampler`, `IpcStats`, `SocketStats`, `register_signal_pipe`, `probe_version` |

### Data Flow — `watch()` block

```
__enter__
  │
  ├─ snapshot_resources()         ← Rust: reads /proc/self/status
  ├─ list_open_fds()              ← Rust: reads /proc/self/fd/
  ├─ threading.enumerate()        ← Python stdlib
  ├─ _count_children()            ← /proc/.../children or pgrep
  └─ BackgroundSampler.start()    ← Rust thread spawned

  [ your code runs ]

__exit__
  │
  ├─ BackgroundSampler.stop()     → returns peak_rss_bytes
  ├─ snapshot_resources()         ← after snapshot
  ├─ list_open_fds()              ← after FD list
  ├─ threading.enumerate()        ← after thread list
  └─ ResourceDelta(...)           ← computed and stored on .result
```

---

## How to Use proctrace

### Installation

```bash
pip install proctrace
```

Build from source (requires Rust + `maturin`):

```bash
pip install maturin
maturin develop --release
```

**Requirements:** Python >= 3.10 · Linux or macOS

---

### Context Manager (`watch`)

The simplest entry point. Wrap any block to measure its resource footprint.

```python
import proctrace

with proctrace.watch() as probe:
    do_work()

print(probe.result.report())
```

**Parameters of `proctrace.watch()`:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `memory` | `bool` | `True` | Track RSS and VMS memory |
| `fds` | `bool` | `True` | Track open file descriptors |
| `threads` | `bool` | `True` | Track thread count and names |
| `children` | `bool` | `True` | Track child process count |
| `sample_interval` | `float` | `0.1` | Background peak-RSS poll interval (seconds) |

After the `with` block, `probe.result` is a `ResourceDelta`.

---

### Decorator (`@probe`)

Attach resource tracking to any function — sync or async — without changing its call site.

```python
from proctrace.decorators import probe

@probe(memory=True, fds=True, output="stderr")
def load_dataset(path: str) -> list:
    ...

load_dataset("data.csv")

# Access the result afterwards
delta = load_dataset.last_probe_result
print(f"RSS grew by {delta.rss_delta_mb:.2f} MB")
```

**Parameters of `@probe()`:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `memory` | `bool` | `True` | Track RSS / VMS |
| `fds` | `bool` | `True` | Track file descriptors |
| `threads` | `bool` | `True` | Track threads |
| `children` | `bool` | `False` | Track child processes |
| `sample_interval` | `float` | `0.05` | Background sampler interval |
| `output` | `"stderr"` or `"none"` | `"stderr"` | Print report automatically |
| `store` | `bool` | `True` | Store result on `fn.last_probe_result` |

Works identically on `async def` functions.

---

### IPC Tracing

Wrap queues, pipes, and sockets to collect latency and throughput metrics.

```python
import queue, os, socket
from proctrace.ipc import trace_ipc, trace_pipe, trace_socket, ipc_report

# Queues
q = trace_ipc(queue.Queue(), name="task-queue")
q.put(item)
item = q.get()

# OS pipes
r_fd, w_fd = os.pipe()
pipe = trace_pipe(r_fd, w_fd, name="my-pipe")
pipe.write(b"hello")
data = pipe.read(5)

# Sockets
raw_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock = trace_socket(raw_sock, name="worker-conn")
sock.sendall(b"ping")
resp = sock.recv(1024)

# Print aggregated report for all traced channels
print(ipc_report())
```

All traced wrappers are transparent — they support the same interface as their underlying object.

---

### On-demand Stack Dumps

Install a signal handler so you can trigger a full thread + asyncio task dump at any time without stopping the process.

```python
import proctrace

proctrace.install_signal_handler(sig="SIGUSR1")

# From another terminal:
#   kill -USR1 <pid>
```

**Parameters of `install_signal_handler()`:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sig` | `str` | `"SIGUSR1"` | Signal to listen for (`SIGUSR1`, `SIGUSR2`, `SIGALRM`) |
| `output` | `str` or `IO` | `"stderr"` | `"stderr"`, a file path string, or a file-like object |
| `include_asyncio` | `bool` | `True` | Also dump asyncio tasks |
| `loop` | `EventLoop or None` | `None` | Specific loop to inspect; auto-detected if `None` |

The dump includes a timestamped header, each thread's last 10 stack frames, and up to 5 frames per asyncio task.

---

### CLI

```
proctrace <subcommand> [options]
```

#### `proctrace run` — measure a subprocess

```bash
proctrace run -- python myscript.py
proctrace run --json -- python myscript.py   # JSON to stdout
```

#### `proctrace watch` — live memory polling

```bash
proctrace watch --pid <PID> --interval 1.0 --duration 30
```

Prints a live-updating table of RSS and VMS (MB) for the target process.

#### `proctrace dump` — trigger a stack dump

```bash
proctrace dump --pid <PID> --signal SIGUSR1
```

Sends a signal to a running proctrace-instrumented process to trigger a thread dump on its stderr.

---

## API Reference

### `ResourceDelta`

A dataclass produced after every measurement. All fields reflect the **delta** between entry and exit of the watched block.

| Attribute | Type | Description |
|---|---|---|
| `rss_delta_bytes` | `int` | RSS change in bytes (can be negative) |
| `vms_delta_bytes` | `int` | Virtual memory size change |
| `fd_delta` | `int` | Open file descriptor count change |
| `peak_rss_bytes` | `int` | Highest RSS observed by the background sampler |
| `thread_delta` | `int` | Thread count change |
| `child_delta` | `int` | Child process count change |
| `elapsed_ns` | `int` | Wall-clock time of block in nanoseconds |
| `leaked_fds` | `list[str]` | FD paths open at exit but not at entry |
| `new_thread_names` | `list[str]` | Names of threads created during the block |

**Convenience properties:**

| Property | Returns |
|---|---|
| `.rss_delta_mb` | `float` — RSS delta in megabytes |
| `.vms_delta_mb` | `float` — VMS delta in megabytes |
| `.peak_rss_mb` | `float` — Peak RSS in megabytes |
| `.elapsed_ms` | `float` — Elapsed time in milliseconds |

**Serialization:**

```python
d    = delta.to_dict()           # -> dict[str, Any]
j    = delta.to_json(indent=2)   # -> JSON string
copy = ResourceDelta.from_dict(d)
```

**Formatted report:**

```python
print(delta.report())   # colour-coded when stderr is a TTY
```

---

## Code Snippets

See the [`guide-codesnippet/`](./guide-codesnippet/) folder for runnable examples:

| File | What it demonstrates |
|---|---|
| [`01_basic_watch.py`](./guide-codesnippet/01_basic_watch.py) | Minimal `watch()` context manager |
| [`02_selective_tracking.py`](./guide-codesnippet/02_selective_tracking.py) | Enabling only specific metrics |
| [`03_probe_decorator.py`](./guide-codesnippet/03_probe_decorator.py) | `@probe` on sync and async functions |
| [`04_json_export.py`](./guide-codesnippet/04_json_export.py) | Serialising results to JSON / dict |
| [`05_fd_leak_detection.py`](./guide-codesnippet/05_fd_leak_detection.py) | Detecting file descriptor leaks |
| [`06_ipc_tracing.py`](./guide-codesnippet/06_ipc_tracing.py) | Tracing queues, pipes, and sockets |
| [`07_signal_dump.py`](./guide-codesnippet/07_signal_dump.py) | On-demand thread + asyncio dump via signal |
| [`08_cli_usage.sh`](./guide-codesnippet/08_cli_usage.sh) | CLI `run`, `watch`, and `dump` commands |
