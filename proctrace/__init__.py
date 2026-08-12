from __future__ import annotations

from proctrace._proctrace_core import probe_version as _probe_version

# the version string inn in rust's side
__version__: str = _probe_version()

__all__ = ["__version__"]
