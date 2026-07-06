"""Bridge between the Evolve engine (box 1) and the platform's Evolve UI work queue.

The engine pushes a parked gate's review packet to the platform over HTTP (POST /gates),
where the operator sees it and decides; a poller reads decided rows back so the engine
can resume. This is the box-1 -> platform side of the work-queue design. stdlib
only. Config via env (set in .env — no operator-specific host or credential is committed):
    EVOLVE_SERVER_URL     the Evolve dashboard base URL; defaults to localhost only
    EVOLVE_SERVICE_TOKEN  long-lived service token (auth; optional for a loopback
                          token-less dev dashboard)
"""
import json
import os
import urllib.request


def _base() -> str:
    return (os.getenv("EVOLVE_SERVER_URL") or "http://localhost:8000").rstrip("/")


def _post(path: str, body: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(_base() + path, data=json.dumps(body).encode(),
                                 method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _get(path: str, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(_base() + path, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def auth() -> str | None:
    """The service token the engine authenticates with (EVOLVE_SERVICE_TOKEN — its
    is_service role permits POSTing gates but NOT deciding them). Returns None when no
    token is configured: the dashboard's token-less local-dev mode (loopback only)
    accepts unauthenticated mutations, so requests are simply sent bare."""
    return os.getenv("EVOLVE_SERVICE_TOKEN") or None


# --- offline outbox -----------------------------------------------------------
# The dashboard can go down during a redeploy. Rather than lose the agents' status/gate
# post-backs, buffer them on the brain and flush in FIFO order once the dashboard is reachable
# again — every write reconciles on the dashboard, in order, when it's back up.
import socket
import urllib.error

_OUTBOX = os.path.expanduser(os.getenv("EVOLVE_OUTBOX", "~/.evolve/outbox.jsonl"))


def _is_conn_error(e: Exception) -> bool:
    # connection-level failure (dashboard down/unreachable) — NOT an HTTP status error.
    if isinstance(e, urllib.error.HTTPError):
        return False
    return isinstance(e, (urllib.error.URLError, socket.timeout, ConnectionError, OSError))


def _is_transient_http(e: Exception) -> bool:
    """HTTP errors worth KEEPING in the queue: 5xx (dashboard restarting/broken),
    429 (throttled), and 401/403 (token rotation mid-buffer — the operator fixes the
    token and the queue drains). Only a permanent 4xx (bad request/unknown route) is
    poison to drop; dropping a buffered gate push on a transient error would strand
    the work item parked forever with no gate card the operator can ever see."""
    return isinstance(e, urllib.error.HTTPError) and (
        e.code >= 500 or e.code in (401, 403, 429))


class _outbox_lock:
    """Cross-process file lock around outbox read-modify-write. evolve CLIs run as
    separate short-lived processes; without this, two concurrent flush/enqueue calls
    clobber each other's entries (one rewrites the file while the other appends)."""

    def __enter__(self):
        os.makedirs(os.path.dirname(_OUTBOX) or ".", exist_ok=True)
        self._fh = open(_OUTBOX + ".lock", "w")
        try:
            import fcntl
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        except ImportError:  # non-POSIX: best-effort (single-writer setups)
            pass
        return self

    def __exit__(self, *exc):
        try:
            import fcntl
            fcntl.flock(self._fh, fcntl.LOCK_UN)
        except ImportError:
            pass
        self._fh.close()
        return False


def _enqueue(path: str, body: dict) -> None:
    with _outbox_lock():
        with open(_OUTBOX, "a") as f:
            f.write(json.dumps({"path": path, "body": body}) + "\n")


def _flush() -> None:
    """Deliver buffered post-backs in order; stop at the first connection/transient
    error (dashboard down, restarting, or token rotated) — keep those and the rest."""
    if not os.path.exists(_OUTBOX):
        return
    with _outbox_lock():
        if not os.path.exists(_OUTBOX):
            return
        lines = [l for l in open(_OUTBOX).read().splitlines() if l.strip()]
        if not lines:
            return
        token = auth()
        done = 0
        for line in lines:
            try:
                item = json.loads(line)
                _post(item["path"], item["body"], token)
                done += 1
            except Exception as e:
                if _is_conn_error(e) or _is_transient_http(e):
                    break                        # still down / retryable — keep this and the rest
                # genuinely poison (bad payload, permanent 4xx): drop it, but say so —
                # a silent drop of a gate push is exactly the failure this queue exists to stop.
                import sys
                print(f"evolve outbox: dropping poison entry ({e}): {line[:200]}", file=sys.stderr)
                done += 1
        tail = lines[done:]
        if tail:
            open(_OUTBOX, "w").write("\n".join(tail) + "\n")
        elif os.path.exists(_OUTBOX):
            os.remove(_OUTBOX)


def _send(path: str, body: dict) -> dict:
    """Resilient write: flush any backlog first, then post — buffering this one if the
    dashboard is down or answering with a transient error."""
    _flush()
    try:
        return _post(path, body, auth())
    except Exception as e:
        if _is_conn_error(e) or _is_transient_http(e):
            _enqueue(path, body)
            return {"queued": True, "path": path}
        raise


def push_gate(packet: dict, token: str | None = None) -> dict:
    """Surface a parked gate in the operator's work queue (on the dashboard). Buffered if the dashboard is down."""
    return _send("/api/apps/evolve/gates", {
        "instance_id": packet.get("instance"),
        "gate": packet.get("gate"),
        "packet": packet,
    })


def list_decided(token: str | None = None) -> list[dict]:
    """Gates the operator has decided in the UI (for the resume poller). If the dashboard is unreachable
    (e.g. mid redeploy), return [] — no decisions are visible right now; the loop keeps
    working new GitHub issues and reconciles once the dashboard is back. Never let a dashboard outage crash it.

    FLUSH-FIRST: the loop calls this at the START of every pass (its decided-gate scan), so draining
    the outbox here guarantees buffered reports go out even for a PARKED item whose own pass does no
    `_send` — otherwise a terminal report buffered during a dashboard restart (e.g. a Gate-2 push) could
    strand until some *other* item happened to write. `_flush` is a no-op when the outbox is empty and
    self-handles a still-down dashboard (keeps the queue), so this is cheap and safe every pass."""
    _flush()
    try:
        return _get("/api/apps/evolve/gates?status=decided", token or auth()).get("gates", [])
    except Exception as e:
        if _is_conn_error(e):
            return []
        raise


def resolve(instance_id: str, status: str, token: str | None = None) -> dict:
    """Mark a decided gate's terminal outcome after the engine resumed it. Buffered if the dashboard is down."""
    return _send(f"/api/apps/evolve/gates/{instance_id}/resolve", {"status": status})


def decide(instance_id: str, decision: str, note: str = "", token: str | None = None) -> dict:
    """Record a gate decision via the service token. The server only permits a service token
    to APPROVE gate 2 (validate) — the two-token carve-out — and 403s a service approve on
    gate 1/3. The loop uses this to AUTO-APPROVE a green-validated build (recorded as
    decided_by='auto'); it never decides requirements or UAT. Buffered if the dashboard is down."""
    return _send(f"/api/apps/evolve/gates/{instance_id}/decision",
                 {"decision": decision, "note": note})


def report_run(instance_id: str, *, title="", source="", phase="", status="",
               current_agent="", current_node="", cost_usd=None, events=None,
               token: str | None = None) -> dict:
    """Report a run's status + a batch of activity events to the mission-control view
    (one POST does both). Best-effort observability — buffered if the dashboard is down, flushed in
    order when it's back, so a redeploy never loses run/event updates."""
    return _send("/api/apps/evolve/runs", {
        "instance_id": instance_id, "title": title, "source": source, "phase": phase,
        "status": status, "current_agent": current_agent, "current_node": current_node,
        "cost_usd": cost_usd, "events": events or [],
    })
