from __future__ import annotations

import pathlib

from proctrace._proctrace_core import probe_version as _probe_version
from proctrace._types import ResourceDelta
from proctrace.ipc import ipc_report, trace_ipc, trace_pipe, trace_socket
from proctrace.snapshot import install_signal_handler
from proctrace.watch import ResourceWatcher, watch

__version__: str = _probe_version()

_GUIDE_PATH = pathlib.Path(__file__).parent.parent / "GUIDE.md"


def help() -> None:
    if _GUIDE_PATH.exists():
        print(_GUIDE_PATH.read_text())
    else:
        print("Guide not found. See the project repository for documentation.")


__all__ = [
    "ResourceDelta",
    "ResourceWatcher",
    "__version__",
    "help",
    "watch",
    "install_signal_handler",
    "trace_ipc",
    "trace_pipe",
    "trace_socket",
    "ipc_report",
]
