from __future__ import annotations

from proctrace._proctrace_core import probe_version as _probe_version
from proctrace._types import ResourceDelta
from proctrace.snapshot import install_signal_handler
from proctrace.watch import ResourceWatcher, watch

__version__: str = _probe_version()

__all__ = ["ResourceDelta", "ResourceWatcher", "__version__", "watch", "install_signal_handler"]
