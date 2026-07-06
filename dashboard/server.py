"""Standalone Evolve dashboard backend (FastAPI).

Serves the REST contract the engine CLIs already call under the /api/apps/evolve
prefix (engine/platform_bridge.py, scripts/evolve_explain.py, evolve_decide.py,
evolve_runs.py work unchanged) plus a minimal placeholder for the operator's
gate-review SPA (the real frontend is a later piece).

AUTH model (the core safety invariant):
  * Bearer <token> in the Authorization header.
  * principal == "decide"  if token == EVOLVE_DECIDE_TOKEN  (operator / parent role)
  * principal == "service" if token == EVOLVE_SERVICE_TOKEN (the brain / loop)
  * GET endpoints need no auth (matches the engine's current behavior).
  * Mutations: service-or-decide ...
  * EXCEPT gates/{id}/decision, runs/{id}/archive, runs/{id}/reverify which REQUIRE
    the DECIDE token. The engine can PUSH but it can NEVER DECIDE.
  * Local dev: if BOTH tokens are unset, mutations are allowed — but a SERVICE token,
    when one IS set, is STILL rejected at the decision endpoint (never let service decide).
"""
import hmac
import os
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from .store import Store

# --- config (from the repo-root .env) ----------------------------------------
_ROOT = Path(__file__).resolve().parent.parent  # repo root


def _load_dotenv() -> None:
    envf = _ROOT / ".env"
    if not envf.exists():
        return
    for line in envf.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

DECIDE_TOKEN = os.getenv("EVOLVE_DECIDE_TOKEN") or ""
SERVICE_TOKEN = os.getenv("EVOLVE_SERVICE_TOKEN") or ""
DB_PATH = os.getenv("EVOLVE_DASHBOARD_DB") or "~/.evolve/dashboard.db"
PORT = int(os.getenv("EVOLVE_DASHBOARD_PORT") or os.getenv("PORT") or "8000")
GITHUB_REPO = os.getenv("GITHUB_REPO") or ""

STATIC_DIR = Path(__file__).resolve().parent / "static"

try:
    _VERSION = (_ROOT / "VERSION").read_text(encoding="utf-8").strip()
except OSError:
    _VERSION = "0.0.0"

app = FastAPI(title="Evolve dashboard", version=_VERSION)
store = Store(DB_PATH)

PREFIX = "/api/apps/evolve"


# --- auth ---------------------------------------------------------------------
def _principal(authorization: str | None) -> str | None:
    """Return 'decide', 'service', or None for an Authorization header value."""
    if not authorization:
        return None
    tok = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else authorization.strip()
    if not tok:
        return None
    if DECIDE_TOKEN and hmac.compare_digest(tok, DECIDE_TOKEN):
        return "decide"
    if SERVICE_TOKEN and hmac.compare_digest(tok, SERVICE_TOKEN):
        return "service"
    return "unknown"


def _require_mutator(authorization: str | None) -> str:
    """A service-or-decide mutation. Local dev (no tokens configured) is allowed."""
    p = _principal(authorization)
    if p in ("decide", "service"):
        return p
    if not DECIDE_TOKEN and not SERVICE_TOKEN:
        return "dev"  # local dev: tokens unset → allow
    raise HTTPException(status_code=401, detail="valid service or decide token required")


def _require_decide(authorization: str | None) -> str:
    """A decide-ONLY mutation. A service token is rejected with 403 (the engine can
    push but can never decide). Local dev with NO tokens set is allowed, but a SERVICE
    token presented when one is configured is still 403."""
    p = _principal(authorization)
    if p == "decide":
        return p
    if p == "service":
        raise HTTPException(status_code=403, detail="a service token cannot decide a gate")
    if not DECIDE_TOKEN and not SERVICE_TOKEN:
        return "dev"  # local dev: no tokens configured → allow
    if not DECIDE_TOKEN and SERVICE_TOKEN:
        # decide token not configured but service is — only a service token could be
        # presented, and service must never decide.
        raise HTTPException(status_code=403, detail="decide token not configured; service may not decide")
    raise HTTPException(status_code=403, detail="decide token required")


def _require_decide_for_gate(authorization: str | None, gate_kind: str, decision: str) -> str:
    """Per-gate authorization for a decision.

    Gate 1 (requirements) and gate 3 (verify / UAT) are decide-ONLY — only the operator's
    decide token may act on them. Gate 2 (validate) is the two-token CARVE-OUT: the loop's
    SERVICE token may record an AUTOMATED APPROVE on green validation (recorded as
    decided_by='auto'), but never a change/reject, and never gate 1 or gate 3. So the engine
    can advance a validated build to UAT on its own, yet can never give the two FINAL
    approvals — requirements and UAT — which remain the operator's."""
    p = _principal(authorization)
    if p == "decide":
        return p
    if p == "service":
        if gate_kind == "gate2" and decision == "approve":
            return "auto"
        raise HTTPException(status_code=403,
                            detail="a service token may only auto-approve gate 2 (validate)")
    if not DECIDE_TOKEN and not SERVICE_TOKEN:
        return "dev"  # local dev: no tokens configured → allow
    raise HTTPException(status_code=403, detail="decide token required")


# --- helpers ------------------------------------------------------------------
def _iid(body: dict) -> str:
    """The engine bridge posts 'instance_id'; the original packet uses 'instance'.
    Accept either."""
    return (body.get("instance_id") or body.get("instance") or "").strip()


# ============================== runs =========================================
@app.post(PREFIX + "/runs")
async def post_run(request: Request, authorization: str | None = Header(default=None)):
    _require_mutator(authorization)
    body = await request.json()
    iid = _iid(body)
    if not iid:
        raise HTTPException(status_code=422, detail="instance_id (or instance) is required")
    # derive repo from source (github:owner/repo#n) when the loop didn't set it — otherwise the
    # dashboard's repo filter matches nothing (runs were stored with repo=None).
    _repo = body.get("repo")
    if not _repo:
        _src = body.get("source") or ""
        if _src.startswith("github:") and "#" in _src:
            _repo = _src[len("github:"):].split("#", 1)[0] or None
    store.upsert_run(
        iid,
        repo=_repo,
        title=body.get("title"),
        source=body.get("source"),
        phase=body.get("phase"),
        status=body.get("status"),
        current_agent=body.get("current_agent"),
        current_node=body.get("current_node"),
        cost_usd=body.get("cost_usd"),
    )
    appended = store.add_events(iid, body.get("events") or [])
    return {"ok": True, "instance_id": iid, "events_appended": appended}


@app.get(PREFIX + "/runs")
async def get_runs(archived: int = 0, repo: str | None = None):
    return {"runs": store.list_runs(archived=bool(archived), repo=repo)}


# The intake backlog: admissible open issues the loop hasn't STARTED yet (no run exists), so the
# board can show filed-but-not-yet-started work instead of it being invisible until the loop picks
# it up. Each refresh hits GitHub (via engine.intake), so cache it ~60s. The frontend filters out
# any that already have a run by matching `source`, so this just returns the raw admissible set.
_intake_cache: dict = {"at": 0.0, "data": None}


def _collect_intake() -> list[dict]:
    import sys as _sys
    if str(_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_ROOT))
    from engine import intake as _intake
    pending = []
    for i in _intake.all_admissible_issues():
        repo, num = i.get("repo"), i.get("number")
        if not repo or num is None:
            continue
        pending.append({"repo": repo, "number": num, "title": i.get("title", ""),
                        "source": f"github:{repo}#{num}"})
    return pending


@app.get(PREFIX + "/intake")
async def get_intake():
    import asyncio
    import time as _t
    now = _t.time()
    if _intake_cache["data"] is not None and (now - _intake_cache["at"]) < 60:
        return {"pending": _intake_cache["data"]}
    try:
        # OFF the event loop: a manual-intake repo's allowlist check HTTP-calls THIS
        # server (admitted_numbers -> EVOLVE_SERVER_URL); running it inline blocks the
        # single loop, the inner request can't be served, and intake times out empty.
        pending = await asyncio.to_thread(_collect_intake)
        _intake_cache["at"], _intake_cache["data"] = now, pending
        return {"pending": pending}
    except Exception:
        # never break the board on an intake/GitHub hiccup — serve the last good list (or empty)
        return {"pending": _intake_cache["data"] or []}


@app.get(PREFIX + "/runs/{instance_id}/events")
async def get_run_events(instance_id: str, since: int = 0):
    return {"events": store.events(instance_id, since=since)}


@app.post(PREFIX + "/runs/{instance_id}/archive")
async def archive_run(instance_id: str, authorization: str | None = Header(default=None)):
    _require_decide(authorization)
    if not store.get_run(instance_id):
        raise HTTPException(status_code=404, detail=f"no run {instance_id}")
    store.set_archived(instance_id, True)
    return {"ok": True, "instance_id": instance_id, "archived": True}


@app.post(PREFIX + "/runs/{instance_id}/reverify")
async def reverify_run(instance_id: str, authorization: str | None = Header(default=None)):
    """Re-open a done item's gate3 — set its gate back to status='waiting'."""
    _require_decide(authorization)
    if not store.get_run(instance_id):
        raise HTTPException(status_code=404, detail=f"no run {instance_id}")
    if not store.get_gate(instance_id):
        # never fabricate a blank, packet-less gate card for a run that has no gate row
        raise HTTPException(status_code=404, detail=f"no gate to re-open for {instance_id}")
    # Re-open the gate (waiting) without clobbering its packet.
    store.upsert_gate(instance_id, gate="gate3", reset=True)
    store.upsert_run(instance_id, status="waiting", phase="verify")
    return {"ok": True, "instance_id": instance_id, "reverify": True}


# ============================== gates ========================================
@app.post(PREFIX + "/gates")
async def post_gate(request: Request, authorization: str | None = Header(default=None)):
    _require_mutator(authorization)
    body = await request.json()
    iid = _iid(body)
    if not iid:
        raise HTTPException(status_code=422, detail="instance_id (or instance) is required")
    packet = body.get("packet")
    if not isinstance(packet, dict):
        packet = None
    gate = body.get("gate") or (packet.get("gate") if packet else None)
    title = body.get("title") or (packet.get("title") if packet else None)
    if not title and packet:
        title = (packet.get("work_item") or {}).get("title")
    rec = (packet.get("recommendation") if packet else None) or body.get("recommendation") or {}
    # derive repo from the gate packet's work_item.source (run-reporting often omits source) so the
    # dashboard repo filter works for every item — every item passes through a gate.
    _grepo = body.get("repo") or (packet.get("repo") if packet else None)
    if not _grepo and packet:
        _gsrc = ((packet.get("work_item") or {}).get("source") or "")
        if _gsrc.startswith("github:") and "#" in _gsrc:
            _grepo = _gsrc[len("github:"):].split("#", 1)[0]
    store.upsert_gate(
        iid,
        gate=gate,
        repo=_grepo,
        title=title,
        rec_action=rec.get("action"),
        rec_why=rec.get("why") or rec.get("rationale"),
        packet=packet,
    )
    if _grepo:
        store.upsert_run(iid, repo=_grepo)  # tag the run too (COALESCE-safe)
    return {"ok": True, "instance_id": iid, "status": "waiting"}


@app.get(PREFIX + "/gates")
async def get_gates(status: str | None = None, repo: str | None = None):
    return {"gates": store.list_gates(status=status, repo=repo)}


@app.get(PREFIX + "/gates/{instance_id}")
async def get_gate(instance_id: str):
    g = store.get_gate(instance_id)
    if not g:
        raise HTTPException(status_code=404, detail=f"no gate {instance_id}")
    return g


@app.post(PREFIX + "/gates/{instance_id}/decision")
async def post_decision(instance_id: str, body: dict = Body(...),
                        authorization: str | None = Header(default=None)):
    decision = (body.get("decision") or "").strip()
    if decision not in ("approve", "change", "reject"):
        raise HTTPException(status_code=422, detail="decision must be approve|change|reject")
    gate = store.get_gate(instance_id)
    if not gate:
        raise HTTPException(status_code=404, detail=f"no gate {instance_id}")
    # Per-gate auth: gate1/gate3 are operator-only; gate2 may be auto-approved by the loop.
    principal = _require_decide_for_gate(authorization, (gate.get("gate") or ""), decision)
    note = body.get("note") or ""
    if not store.record_decision(instance_id, decision=decision, note=note, decided_by=principal):
        raise HTTPException(status_code=404, detail=f"no gate {instance_id}")
    return {"ok": True, "instance_id": instance_id, "decision": decision,
            "status": "decided", "decided_by": principal}


@app.post(PREFIX + "/gates/{instance_id}/resolve")
async def post_resolve(instance_id: str, body: dict = Body(default={}),
                       authorization: str | None = Header(default=None)):
    _require_mutator(authorization)
    status = (body or {}).get("status") or "resolved"
    if not store.resolve_gate(instance_id, status):
        raise HTTPException(status_code=404, detail=f"no gate {instance_id}")
    return {"ok": True, "instance_id": instance_id, "status": status}


# ============================== repos ========================================
@app.get(PREFIX + "/repos")
async def get_repos():
    """The repo collection for the repo-switcher — read from the registry (evolve.repos.yaml),
    falling back to the single $GITHUB_REPO when no registry is configured."""
    try:
        import sys as _sys
        if str(_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_ROOT))
        from engine import repos as _repos
        rows = _repos.load_repos()
        if rows:
            return [{"name": r.get("name"), "type": r.get("type", ""),
                     "intake": _repos.repo_intake(r.get("name"))} for r in rows]
    except Exception:
        pass
    return [{"name": GITHUB_REPO}] if GITHUB_REPO else []


# ========================= issue intake allowlist ============================
# Manual-intake repos process ONLY issues a human has admitted here — a human reads the issue
# on GitHub first, so a malicious/prompt-injection issue never reaches an agent. Admitting is an
# operator TRUST decision, so it requires the decide token (a service token is rejected).
@app.get(PREFIX + "/admitted")
async def get_admitted(repo: str | None = None):
    rows = store.list_admitted(repo)
    return {"admitted": [r["number"] for r in rows], "rows": rows}


@app.post(PREFIX + "/admit")
async def admit_issue(request: Request, authorization: str | None = Header(default=None)):
    _require_decide(authorization)
    body = await request.json()
    repo = (body.get("repo") or "").strip()
    number = body.get("number")
    if not repo or number in (None, ""):
        raise HTTPException(status_code=422, detail="repo and number are required")
    try:
        number = int(number)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="number must be an integer")
    store.admit_issue(repo, number, added_by="operator")
    return {"ok": True, "repo": repo, "number": number, "admitted": True}


@app.post(PREFIX + "/admit/revoke")
async def revoke_admit(request: Request, authorization: str | None = Header(default=None)):
    _require_decide(authorization)
    body = await request.json()
    repo = (body.get("repo") or "").strip()
    number = body.get("number")
    if not repo or number in (None, ""):
        raise HTTPException(status_code=422, detail="repo and number are required")
    store.revoke_issue(repo, int(number))
    return {"ok": True, "repo": repo, "number": int(number), "admitted": False}


# ============================== root / static ================================
@app.get("/")
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        # no-cache so board/JS updates take effect on the next load without a manual hard-refresh
        return FileResponse(str(index), headers={"Cache-Control": "no-cache, must-revalidate"})
    return JSONResponse({"detail": "Evolve dashboard — SPA pending"})


def main() -> None:
    import uvicorn

    # Default to loopback. Binding a non-loopback interface (EVOLVE_DASHBOARD_BIND=0.0.0.0
    # so the brain host can reach the dashboard) REQUIRES the auth tokens: token-less "dev
    # mode" on a network interface would let anyone on the LAN decide gates and admit issues.
    host = os.getenv("EVOLVE_DASHBOARD_BIND") or "127.0.0.1"
    if host not in ("127.0.0.1", "localhost", "::1") and not (DECIDE_TOKEN or SERVICE_TOKEN):
        raise SystemExit(
            "refusing to bind {!r} with no EVOLVE_DECIDE_TOKEN/EVOLVE_SERVICE_TOKEN set — "
            "token-less mode is for loopback only. Set the tokens in .env, or leave "
            "EVOLVE_DASHBOARD_BIND unset for local dev.".format(host))
    uvicorn.run("dashboard.server:app", host=host, port=PORT, reload=False)


if __name__ == "__main__":
    main()
