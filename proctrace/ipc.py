from __future__ import annotations

import os
import time
from typing import Any

from proctrace._proctrace_core import IpcStats

_registry: list[IpcStats] = []


def _register(stats: IpcStats) -> IpcStats:
    _registry.append(stats)
    return stats


def ipc_report() -> str:
    if not _registry:
        return "(no IPC channels traced)"
    return "\n".join(s.report() for s in _registry)

class TracedQueue:
    __slots__ = ("_q", "_stats", "_put_times")

    def __init__(self, queue: Any, stats: IpcStats) -> None:
        self._q = queue
        self._stats = stats
        self._put_times: dict[int, int] = {}

    def put(self, item: Any, block: bool = True, timeout: float | None = None) -> None:
        t_put_ns = time.monotonic_ns()
        self._q.put(item, block=block, timeout=timeout)
        self._put_times[id(item)] = t_put_ns

        try:
            self._stats.record_depth(self._q.qsize())
        except NotImplementedError:
            pass

    def put_nowait(self, item: Any) -> None:
        self.put(item, block=False)

    def get(self, block: bool = True, timeout: float | None = None) -> Any:
        item = self._q.get(block=block, timeout=timeout)
        t_get_ns = time.monotonic_ns()

        t_put_ns = self._put_times.pop(id(item), None)
        if t_put_ns is not None:
            latency_us = (t_get_ns - t_put_ns) // 1000
            self._stats.record_latency_us(latency_us)

        return item

    def get_nowait(self) -> Any:
        return self.get(block=False)

    @property
    def stats(self) -> IpcStats:
        return self._stats

    def __getattr__(self, name: str) -> Any:
        return getattr(self._q, name)


class TracedPipe:
    __slots__ = ("read_fd", "write_fd", "_stats", "_write_times")

    def __init__(self, read_fd: int, write_fd: int, stats: IpcStats) -> None:
        self.read_fd = read_fd
        self.write_fd = write_fd
        self._stats = stats
        self._write_times: list[int] = []

    def write(self, data: bytes) -> int:
        t_write_ns = time.monotonic_ns()
        n = os.write(self.write_fd, data)
        self._write_times.append(t_write_ns)
        return n

    def read(self, n: int) -> bytes:
        data = os.read(self.read_fd, n)
        t_read_ns = time.monotonic_ns()
        if self._write_times:
            t_write_ns = self._write_times.pop(0)
            latency_us = (t_read_ns - t_write_ns) // 1000
            self._stats.record_latency_us(latency_us)
        return data

    def fileno_read(self) -> int:
        return self.read_fd

    def fileno_write(self) -> int:
        return self.write_fd

    @property
    def stats(self) -> IpcStats:
        return self._stats


def trace_ipc(queue: Any, name: str = "", ring_capacity: int = 1024) -> TracedQueue:
    channel_name = name or repr(queue)[:40]
    stats = IpcStats(channel_name, ring_capacity)
    _register(stats)
    return TracedQueue(queue, stats)


def trace_pipe(
    read_fd: int,
    write_fd: int,
    name: str = "",
    ring_capacity: int = 1024,
) -> TracedPipe:

    channel_name = name or f"pipe({read_fd},{write_fd})"
    stats = IpcStats(channel_name, ring_capacity)
    _register(stats)
    return TracedPipe(read_fd, write_fd, stats)
