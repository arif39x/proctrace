from __future__ import annotations

import functools
import inspect
import sys
from collections.abc import Callable
from typing import Literal, TypeVar

from proctrace._types import ResourceDelta
from proctrace.watch import ResourceWatcher

F = TypeVar("F", bound=Callable)


def probe(
    *,
    memory: bool = True,
    fds: bool = True,
    threads: bool = True,
    children: bool = False,        
    sample_interval: float = 0.05,  
    output: Literal["stderr", "none"] = "stderr",
    store: bool = True,
) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        if inspect.iscoroutinefunction(fn):
            return _wrap_async(fn, memory, fds, threads, children, sample_interval, output, store)
        else:
            return _wrap_sync(fn, memory, fds, threads, children, sample_interval, output, store)
    return decorator


def _wrap_sync(fn, memory, fds, threads, children, sample_interval, output, store):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        watcher = ResourceWatcher(
            memory=memory, fds=fds, threads=threads,
            children=children, sample_interval=sample_interval,
        )
        with watcher:
            result = fn(*args, **kwargs)

        _handle_result(wrapper, watcher.result, output, store)
        return result

    wrapper.last_probe_result = None  
    return wrapper  


def _wrap_async(fn, memory, fds, threads, children, sample_interval, output, store):
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        watcher = ResourceWatcher(
            memory=memory, fds=fds, threads=threads,
            children=children, sample_interval=sample_interval,
        )
        with watcher:
            result = await fn(*args, **kwargs)

        _handle_result(wrapper, watcher.result, output, store)
        return result

    wrapper.last_probe_result = None  
    return wrapper  


def _handle_result(
    wrapper: Callable,
    delta: ResourceDelta | None,
    output: str,
    store: bool,
) -> None:
    if delta is None:
        return
    if store:
        wrapper.last_probe_result = delta
    if output == "stderr":
        print(delta.report(), file=sys.stderr)