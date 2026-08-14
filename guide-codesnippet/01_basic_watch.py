import time
import proctrace


def simulate_work() -> list[bytes]:
    """Allocate ~10 MB and hold it for a moment."""
    data = [b"x" * 1024 * 1024 for _ in range(10)]   # 10 x 1 MB chunks
    time.sleep(0.05)
    return data


with proctrace.watch() as probe:
    result_data = simulate_work()

# .result is a ResourceDelta dataclass
delta = probe.result
print(delta.report())

# You can also access individual fields directly:
print(f"\nRSS delta : {delta.rss_delta_mb:+.2f} MB")
print(f"Peak RSS  : {delta.peak_rss_mb:.2f} MB")
print(f"Elapsed   : {delta.elapsed_ms:.1f} ms")
