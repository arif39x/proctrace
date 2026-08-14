import json
import time
import proctrace
from proctrace import ResourceDelta


# ── Capture a delta ───────────────────────────────────────────────

with proctrace.watch() as probe:
    buf = bytearray(8 * 1024 * 1024)   # 8 MB
    time.sleep(0.02)

delta = probe.result


# ── to_dict() ─────────────────────────────────────────────────────

d = delta.to_dict()
print("--- to_dict() ---")
for k, v in d.items():
    print(f"  {k}: {v!r}")
print()


# ── to_json() ─────────────────────────────────────────────────────

j = delta.to_json(indent=2)
print("--- to_json() ---")
print(j)
print()


# ── Round-trip: from_dict() ───────────────────────────────────────

restored: ResourceDelta = ResourceDelta.from_dict(json.loads(j))
print("--- round-trip from_dict() ---")
print(f"  rss_delta_mb : {restored.rss_delta_mb:+.2f} MB")
print(f"  peak_rss_mb  : {restored.peak_rss_mb:.2f} MB")
print(f"  elapsed_ms   : {restored.elapsed_ms:.1f} ms")
print()


# ── CI-style assertion ────────────────────────────────────────────

MAX_RSS_GROWTH_MB = 50.0

if delta.rss_delta_mb > MAX_RSS_GROWTH_MB:
    raise RuntimeError(
        f"Memory budget exceeded: {delta.rss_delta_mb:.2f} MB "
        f"> {MAX_RSS_GROWTH_MB} MB"
    )
print(f"Memory budget OK: {delta.rss_delta_mb:+.2f} MB (limit {MAX_RSS_GROWTH_MB} MB)")
