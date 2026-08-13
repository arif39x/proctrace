import os
import queue
import proctrace
from proctrace.ipc import _registry


def test_ipc_queue_tracing():
    _registry.clear()
    q = queue.Queue(maxsize=100)
    tq = proctrace.trace_ipc(q, name="test_queue")

    # Put and get 10 items
    for i in range(10):
        tq.put(f"item-{i}")
        assert tq.get() == f"item-{i}"

    stats = tq.stats
    assert stats.total_messages() == 10
    assert stats.avg_latency_us() >= 0.0
    assert stats.peak_depth() >= 1

    report = proctrace.ipc_report()
    assert "test_queue" in report
    assert "10 msgs" in report


def test_ipc_pipe_tracing():
    _registry.clear()
    r_fd, w_fd = os.pipe()
    try:
        tp = proctrace.trace_pipe(r_fd, w_fd, name="test_pipe")
        msg = b"hello world"
        tp.write(msg)
        res = tp.read(len(msg))
        assert res == msg

        stats = tp.stats
        assert stats.total_messages() == 1
        assert stats.avg_latency_us() >= 0.0

        report = proctrace.ipc_report()
        assert "test_pipe" in report
        assert "1 msgs" in report
    finally:
        os.close(r_fd)
        os.close(w_fd)


def test_ring_buffer_capacity():
    _registry.clear()
    q = queue.Queue()
    tq = proctrace.trace_ipc(q, name="cap_queue", ring_capacity=5)

    for i in range(10):
        tq.put(i)
        tq.get()

    assert tq.stats.total_messages() == 10
    # Average and p99 operate on the capped ring buffer of 5 items
    assert tq.stats.avg_latency_us() >= 0.0
