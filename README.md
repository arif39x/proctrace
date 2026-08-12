# proctrace

Non-invasive process and OS state introspection for Python developers.

Diagnose memory leaks, file descriptor leaks, race conditions, and IPC bottlenecks
with a single import — no agents, no profilers, no code changes.

```python
import proctrace

with proctrace.watch() as probe:
    your_code_here()

print(probe.result.report())
```

**Status:** Under construction.

**Platform support:** Linux ✓ · macOS ✓ · Windows ✗
