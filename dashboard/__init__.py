"""Evolve dashboard — standalone FastAPI backend + SQLite store.

Replaces the in-platform "Evolve app" the engine used to report into. Serves the
REST contract the engine CLIs already call (engine/platform_bridge.py,
scripts/evolve_explain.py, scripts/evolve_decide.py, scripts/evolve_runs.py) under
the /api/apps/evolve prefix, plus the operator's gate-review surface.
"""

__all__ = ["store", "server"]
