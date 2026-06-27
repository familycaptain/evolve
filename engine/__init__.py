"""Evolve — a self-maintaining SDLC engine (engine package).

`__version__` is sourced from the repo-root `VERSION` file (single source of truth).
"""
import os as _os


def _read_version() -> str:
    try:
        with open(_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "VERSION"),
                  encoding="utf-8") as _fh:
            return _fh.read().strip()
    except OSError:
        return "0.0.0"


__version__ = _read_version()
