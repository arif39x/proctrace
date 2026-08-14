import time
import proctrace


# --- Memory only, no FD / thread / child tracking ---
print("=== memory only ===")
with proctrace.watch(fds=False, threads=False, children=False) as probe:
    buf = bytearray(5 * 1024 * 1024)   # allocate 5 MB
    time.sleep(0.02)

delta = probe.result
print(delta.report())
print()


# --- FD tracking only (e.g. to spot leaks in I/O code) ---
print("=== fd tracking only ===")
with proctrace.watch(memory=False, threads=False, children=False) as probe:
    f = open("/dev/null")
    # intentionally not closing to demonstrate fd_delta > 0
    time.sleep(0.01)
    f.close()   # close it — delta should be 0

delta = probe.result
print(delta.report())
print()


# --- Fast sampler interval for short-lived, bursty allocations ---
print("=== fast sampling (10 ms interval) ===")
with proctrace.watch(sample_interval=0.01) as probe:
    spike = [b"0" * 1024 * 1024 for _ in range(20)]  # 20 MB spike
    del spike
    time.sleep(0.05)

delta = probe.result
print(delta.report())
