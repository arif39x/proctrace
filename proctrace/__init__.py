from __future__ import annotations

from proctrace._proctrace_core import probe_version as _probe_version

__version__: str = _probe_version()

__all__ = ["__version__"]