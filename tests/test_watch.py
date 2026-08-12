import json
import os
import threading
import time

import pytest

import proctrace


def test_watch_reports_positive_rss_delta():
    with proctrace.watch() as p:
        buf = bytearray(20 * 1024 * 1024)
        assert len(buf) == 20 * 1024 * 1024
    assert p.result.rss_delta_bytes > 0
    assert p.result.peak_rss_bytes >= p.result.rss_delta_bytes


def test_watch_peak_catches_memory_freed_before_exit():
    with proctrace.watch() as p:
        buf = bytearray(64 * 1024 * 1024)
        time.sleep(0.3)
        del buf
    assert p.result.peak_rss_bytes >= 64 * 1024 * 1024


def test_watch_detects_leaked_fds(tmp_path):
    files = [tmp_path / f"leak-{i}.txt" for i in range(5)]
    for f in files:
        f.write_text("")
    with proctrace.watch(fds=True) as p:
        fds = [os.open(f, os.O_WRONLY | os.O_CREAT) for f in files]
        assert len(fds) == 5
    assert len(p.result.leaked_fds) == 5


def test_watch_detects_new_threads():
    stop = threading.Event()
    thread = threading.Thread(target=stop.wait, name="day3-sleeper")
    with proctrace.watch(threads=True) as p:
        thread.start()
        time.sleep(0.05)
    stop.set()
    thread.join()
    assert p.result.thread_delta >= 1
    assert "day3-sleeper" in p.result.new_thread_names


def test_watch_report_prints_box_table():
    with proctrace.watch() as p:
        pass
    report = p.result.report()
    assert "ResourceDelta" in report
    assert "┌─" in report and "└" in report


def test_watch_to_json_is_parseable():
    with proctrace.watch() as p:
        pass
    payload = json.loads(p.result.to_json())
    assert payload["rss_delta_bytes"] == p.result.rss_delta_bytes
    assert payload["peak_rss_bytes"] == p.result.peak_rss_bytes
    assert isinstance(payload["leaked_fds"], list)


def test_watch_propagates_exceptions():
    with pytest.raises(RuntimeError), proctrace.watch() as p:
        raise RuntimeError("boom")
    assert p.result is not None
