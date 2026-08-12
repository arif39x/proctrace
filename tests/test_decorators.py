from __future__ import annotations

import asyncio
import io
import sys

import pytest

from proctrace._types import ResourceDelta
from proctrace.decorators import probe


class TestSyncDecorator:
    def test_attaches_last_probe_result(self):
        @probe(memory=True, fds=False, threads=False)
        def simple():
            return 42

        result = simple()
        assert result == 42
        assert simple.last_probe_result is not None
        assert isinstance(simple.last_probe_result, ResourceDelta)

    def test_preserves_return_value(self):
        @probe(output="none")
        def add(a, b):
            return a + b

        assert add(3, 4) == 7

    def test_no_output_when_none(self):
        @probe(output="none")
        def fn():
            bytearray(1024 * 1024)

        captured = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured
        try:
            fn()
        finally:
            sys.stderr = old_stderr

        assert captured.getvalue() == ""

    def test_multiple_calls_update_result(self):
        @probe(output="none")
        def fn(n):
            return bytearray(n * 1024 * 1024)

        fn(1)
        fn(5)
        assert fn.last_probe_result is not None


class TestAsyncDecorator:
    def test_async_function_decorated(self):
        @probe(memory=True, fds=False, threads=False, output="none")
        async def async_fn():
            await asyncio.sleep(0.01)
            return "done"

        result = asyncio.run(async_fn())
        assert result == "done"
        assert async_fn.last_probe_result is not None
        assert isinstance(async_fn.last_probe_result, ResourceDelta)

    def test_async_preserves_exception(self):
        @probe(output="none")
        async def failing():
            raise ValueError("deliberate")

        with pytest.raises(ValueError, match="deliberate"):
            asyncio.run(failing())
