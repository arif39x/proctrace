import asyncio
import os
import threading
import time

import proctrace


# Install the handler — dumps go to stderr by default
proctrace.install_signal_handler(sig="SIGUSR1", include_asyncio=True)

print(f"[pid={os.getpid()}]  Running.  Send SIGUSR1 to trigger a dump.")
print("  e.g.  kill -USR1", os.getpid())
print()


# ── Background threads (will appear in the dump) ──────────────────

def background_worker(name: str) -> None:
    while True:
        time.sleep(0.5)

for i in range(3):
    t = threading.Thread(target=background_worker, args=(f"worker-{i}",), daemon=True)
    t.start()


# ── Async tasks (will appear in the dump) ────────────────────────

async def slow_task(label: str) -> None:
    while True:
        await asyncio.sleep(1)


async def main() -> None:
    tasks = [
        asyncio.create_task(slow_task(f"task-{i}"), name=f"slow-task-{i}")
        for i in range(3)
    ]

    print("Running for 60 seconds.  Send SIGUSR1 any time for a dump.")
    print("Press Ctrl-C to exit.\n")

    try:
        await asyncio.sleep(60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        for t in tasks:
            t.cancel()


asyncio.run(main())
