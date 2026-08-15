from __future__ import annotations

import mmap
import os
import tempfile
import threading
import time
from collections.abc import Generator

import pytest

pytest_plugins = ["pytester"]


def allocate_dirty_mb(n: int) -> mmap.mmap:
    """Allocate n MB of anonymous memory and touch every page.

    Uses mmap directly instead of bytearray: glibc serves freed bytearray
    chunks from a resident cache, so process-RSS deltas are order-dependent
    and tests flake depending on what ran before. A fresh mmap always faults
    in new pages, keeping RSS deltas deterministic.
    """
    total = n * 1024 * 1024
    region = mmap.mmap(-1, total)
    for i in range(0, total, 4096):
        region[i] = 1
    return region


@pytest.fixture
def open_tmp_files() -> Generator[list, None, None]:
    handles: list = []

    def _open(n: int) -> list:
        for _ in range(n):
            f = tempfile.NamedTemporaryFile(delete=False)
            handles.append(f)
        return handles

    yield _open

    for f in handles:
        try:
            f.close()
            os.unlink(f.name)
        except Exception:
            pass


@pytest.fixture
def sleeping_threads() -> Generator:
    """Start n daemon threads that sleep indefinitely. Yield the list. Clean up after test."""
    threads: list[threading.Thread] = []

    def _start(n: int, name_prefix: str = "TestThread") -> list[threading.Thread]:
        for i in range(n):
            t = threading.Thread(
                target=lambda: time.sleep(60),
                name=f"{name_prefix}-{i}",
                daemon=True,
            )
            t.start()
            threads.append(t)
        return threads

    yield _start
    # Daemon threads die with the process — no explicit cleanup needed
