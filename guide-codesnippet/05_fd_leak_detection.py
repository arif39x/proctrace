import tempfile
import os
import proctrace


# ── Example 1: clean block — no leaked FDs ────────────────────────

print("=== clean block ===")
with proctrace.watch(memory=False, threads=False) as probe:
    with open("/dev/null") as f:
        _ = f.read()
    # f is closed on __exit__ of the inner with-block

delta = probe.result
print(delta.report())
if not delta.leaked_fds:
    print("  No leaked FDs. ✓")
print()


# ── Example 2: simulated leak — file opened but not closed ────────

print("=== leaky block ===")

# Create a temp file we can reliably identify
tf = tempfile.NamedTemporaryFile(delete=False, suffix=".leak_demo")
tf.close()

leak_handles: list = []

with proctrace.watch(memory=False, threads=False) as probe:
    # Open three handles and forget to close them
    for _ in range(3):
        leak_handles.append(open(tf.name))   # noqa: SIM115 (intentional)

delta = probe.result
print(delta.report())

if delta.leaked_fds:
    print(f"\n  Detected {len(delta.leaked_fds)} leaked FD(s):")
    for path in delta.leaked_fds:
        print(f"    {path}")
else:
    print("  (leak not detected — OS may use abstract FD names)")

# cleanup
for h in leak_handles:
    h.close()
os.unlink(tf.name)
print()


# ── Example 3: assert no leaks in a test helper ───────────────────

def assert_no_fd_leaks(fn, *args, **kwargs):
    """Call fn(*args) and raise if it leaks file descriptors."""
    with proctrace.watch(memory=False, threads=False) as probe:
        fn(*args, **kwargs)
    delta = probe.result
    if delta.leaked_fds:
        raise AssertionError(
            f"FD leak detected in {fn.__name__!r}: {delta.leaked_fds}"
        )
    print(f"  {fn.__name__}: no FD leaks ✓")


def good_reader(path: str) -> None:
    with open(path) as f:
        f.read()


print("=== assert_no_fd_leaks helper ===")
tf2 = tempfile.NamedTemporaryFile(delete=False)
tf2.write(b"hello")
tf2.close()

assert_no_fd_leaks(good_reader, tf2.name)
os.unlink(tf2.name)
