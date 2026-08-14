import asyncio
import time

from proctrace.decorators import probe


# ── Sync function ─────────────────────────────────────────────────

@probe(memory=True, fds=True, output="stderr")
def process_batch(n: int) -> list[int]:
    """Allocate a list of n integers and do light work."""
    data = list(range(n))
    time.sleep(0.03)
    return data


print("Calling process_batch(500_000)…")
result = process_batch(500_000)      # report prints to stderr automatically

delta = process_batch.last_probe_result
print(f"[sync] RSS delta  : {delta.rss_delta_mb:+.2f} MB")
print(f"[sync] Elapsed    : {delta.elapsed_ms:.1f} ms")
print()


# ── Async function ────────────────────────────────────────────────

@probe(memory=True, threads=True, output="stderr", sample_interval=0.01)
async def fetch_data(delay: float) -> bytes:
    """Simulate an async I/O call."""
    await asyncio.sleep(delay)
    return b"response" * 1024


async def main() -> None:
    print("Calling fetch_data(0.05)…")
    data = await fetch_data(0.05)    # report prints to stderr automatically

    delta = fetch_data.last_probe_result
    print(f"[async] RSS delta : {delta.rss_delta_mb:+.2f} MB")
    print(f"[async] Elapsed   : {delta.elapsed_ms:.1f} ms")


asyncio.run(main())


# ── output="none" — silent, result only ──────────────────────────

@probe(output="none", store=True)
def silent_fn() -> None:
    time.sleep(0.01)


silent_fn()
d = silent_fn.last_probe_result
print(f"\n[silent] elapsed: {d.elapsed_ms:.1f} ms  (no stderr output above)")
