import proctrace
from proctrace import _proctrace_core as core


def test_version_is_set():
    assert isinstance(proctrace.__version__, str)
    assert proctrace.__version__


def test_snapshot_reports_memory_and_fds():
    snap = core.snapshot_resources()
    assert snap.rss_bytes > 0
    assert snap.vms_bytes >= snap.rss_bytes
    assert snap.open_fds > 0
    assert snap.timestamp_ns > 0


def test_snapshot_mb_helpers():
    snap = core.snapshot_resources()
    assert snap.rss_mb() == snap.rss_bytes / 1024**2
    assert snap.vms_mb() == snap.vms_bytes / 1024**2


def test_list_open_fds_returns_paths():
    paths = core.list_open_fds()
    assert len(paths) > 0
    assert all(isinstance(p, str) for p in paths)
