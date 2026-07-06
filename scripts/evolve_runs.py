#!/usr/bin/env python
"""Evolve `/loop` reporting bridge — let the in-session `/loop` Evolve (the `evolve` skill) surface its
run, per-agent activity, and gates in the SAME Evolve UI as production. Thin wrapper over
platform_bridge so the skill can report with one-line CLI calls. Run ids are prefixed `ev-` so the
production poller ignores them (the in-session engine owns its own gate loop). The id is opaque to
this script — it's passed in.

    python scripts/evolve_runs.py run ev-3 --title "Add doc for Backup setup" --source github:..#3 --status running
    python scripts/evolve_runs.py event ev-3 triage agent_end "✓ proceed · feature"
    python scripts/evolve_runs.py emit-file ev-3 spec-author $EVOLVE_STATE_DIR/3/spec.json  # post a big artifact by PATH (keeps it out of the loop's context)
    python scripts/evolve_runs.py gate  ev-3 gate1 $EVOLVE_STATE_DIR/3/gate1.json
    python scripts/evolve_runs.py decision ev-3        # -> {"decision": "approve"|null, "note": ...} (ONE item)
    python scripts/evolve_runs.py pending              # -> [EVERY item with a live operator decision] in ONE dashboard call (the loop's per-pass scan)
    python scripts/evolve_runs.py resolve ev-3 merged  # clear the gate after acting on the decision
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
for _line in (open(os.path.join(ROOT, ".env")) if os.path.exists(".env") else []):
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        _v = _v.strip()
        if _v and _v[0] not in "'\"":
            _v = _v.split(" #", 1)[0].rstrip()   # unquoted inline comment
        os.environ.setdefault(_k.strip(), _v.strip('"').strip("'"))

from engine import platform_bridge as bridge


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("iid")
    for opt in ("title", "source", "phase", "status", "agent", "node"):
        r.add_argument(f"--{opt}", default="")
    e = sub.add_parser("event")
    e.add_argument("iid"); e.add_argument("agent"); e.add_argument("kind"); e.add_argument("message")
    # emit-file: post a (large) artifact's contents to the UI log WITHOUT the orchestrator carrying
    # the full text in its context — it passes a PATH; this script reads + posts it. Use for the big
    # emits (full spec, reviewer findings, the diff) you already wrote to $EVOLVE_STATE_DIR/<n>/.
    ef = sub.add_parser("emit-file")
    ef.add_argument("iid"); ef.add_argument("agent"); ef.add_argument("file")
    ef.add_argument("--kind", default="emit")
    g = sub.add_parser("gate")
    g.add_argument("iid"); g.add_argument("gate"); g.add_argument("packet_file")
    d = sub.add_parser("decision"); d.add_argument("iid")
    sub.add_parser("pending")  # bulk: EVERY item with a live operator decision, in ONE dashboard call
    sub.add_parser("stranded")  # local: ONLY run dirs stranded mid-segment (phase new|build|gate2)
    sub.add_parser("parked")    # local: phase=parked items by prioritizer score + promoted_waiting count
    rs = sub.add_parser("resolve"); rs.add_argument("iid"); rs.add_argument("status")
    aa = sub.add_parser("autoapprove"); aa.add_argument("iid")
    aa.add_argument("note", nargs="?", default="Auto-approved: validation GREEN on the test host. (Evolve)")
    c = sub.add_parser("close"); c.add_argument("iid"); c.add_argument("comment", nargs="?", default="")
    sub.add_parser("flush")   # drain the offline outbox to the dashboard now (no-op if empty / dashboard down)
    a = ap.parse_args()

    if a.cmd == "run":
        print(bridge.report_run(a.iid, title=a.title, source=a.source, phase=a.phase,
                                status=a.status, current_agent=a.agent, current_node=a.node))
    elif a.cmd == "event":
        print(bridge.report_run(a.iid, current_agent=a.agent,
                                events=[{"agent": a.agent, "kind": a.kind, "message": a.message}]))
    elif a.cmd == "emit-file":
        text = open(os.path.expanduser(a.file)).read()
        print(bridge.report_run(a.iid, current_agent=a.agent,
                                events=[{"agent": a.agent, "kind": a.kind, "message": text}]))
    elif a.cmd == "gate":
        packet = json.load(open(os.path.expanduser(a.packet_file)))
        packet["instance"] = a.iid
        packet["gate"] = a.gate
        print(bridge.push_gate(packet))
    elif a.cmd == "decision":
        dec = [x for x in bridge.list_decided() if x.get("instance_id") == a.iid]
        print(json.dumps({"decision": dec[0]["decision"] if dec else None,
                          "note": dec[0].get("note") if dec else None,
                          "gate": dec[0].get("gate") if dec else None}))
    elif a.cmd == "pending":
        # ONE dashboard call returns EVERY item with a live operator decision (a decided gate, including a
        # re-opened 'done' item that came back at gate3). The loop iterates THIS short list instead of
        # calling `decision <id>` once per run dir — O(actionable), not O(all-runs-ever) — so the scan
        # stays cheap as closed/done items pile up. Each entry: instance_id + gate + decision + note;
        # route on `gate`, cross-ref the local $EVOLVE_STATE_DIR/<n>/ dir for phase/artifacts.
        items = bridge.list_decided()
        print(json.dumps([{"instance_id": x.get("instance_id"), "gate": x.get("gate"),
                           "decision": x.get("decision"), "note": x.get("note")} for x in items]))
    elif a.cmd == "stranded":
        # Local scan of $EVOLVE_STATE_DIR/*/state.json returning ONLY dirs stranded MID-SEGMENT — phase
        # `new`, `build`, or `gate2` (a pass died before the segment finished). Filtered HERE so the loop
        # never reads all N state.json files into context; it ingests only the few stranded ids. Terminal
        # (done/rejected) and OPERATOR-parked (gate1/verify — your two gates) phases are excluded. `gate2`
        # is LOOP-owned (auto-approved on green validation), NOT parked on the operator, so a gate2 left
        # with no recorded auto-approval IS stranded — resume it (re-run autoapprove → merge). A gate2
        # that WAS auto-approved surfaces in `pending` first (decided), which the loop handles ahead of
        # this scan, so it's merged there and never lingers here.
        # O(stranded), not O(all-runs-ever); tiny metadata only, never packet contents.
        import glob
        base = os.path.expanduser(os.getenv("EVOLVE_STATE_DIR") or "~/.evolve/runs")
        out = []
        for sf in glob.glob(os.path.join(base, "*", "state.json")):
            try:
                st = json.load(open(sf))
            except Exception:
                continue
            if st.get("phase") in ("new", "build", "gate2"):
                out.append({"instance_id": st.get("instance_id"), "phase": st.get("phase")})
        print(json.dumps(out))
    elif a.cmd == "parked":
        # Local scan for phase=`parked` items (the prioritizer's long-tail) with their prioritizer
        # score, highest first — the idle-promote drains these into Gate 1 when the loop is otherwise
        # idle. Also returns `promoted_waiting`: how many already-promoted-from-park items currently
        # sit at Gate 1 (phase=gate1 + promoted_from_park), so the loop can honor the flood cap.
        import glob
        base = os.path.expanduser(os.getenv("EVOLVE_STATE_DIR") or "~/.evolve/runs")
        parked, promoted_waiting = [], 0
        for sf in glob.glob(os.path.join(base, "*", "state.json")):
            try:
                st = json.load(open(sf))
            except Exception:
                continue
            ph = st.get("phase")
            if ph == "parked":
                score = 0
                try:
                    score = (json.load(open(os.path.join(os.path.dirname(sf), "prio.json"))).get("score") or 0)
                except Exception:
                    pass
                parked.append({"instance_id": st.get("instance_id"), "score": score,
                               "title": st.get("title", ""), "repo": st.get("repo", "")})
            elif ph == "gate1" and st.get("promoted_from_park"):
                promoted_waiting += 1
        parked.sort(key=lambda x: x["score"], reverse=True)
        print(json.dumps({"parked": parked, "promoted_waiting": promoted_waiting}))
    elif a.cmd == "resolve":
        out = bridge.resolve(a.iid, a.status)
        # Keep the run row in lockstep with the gate outcome so it can never be left "running"
        # after a terminal gate (the two-step "resolve then report status" used to drop the 2nd).
        run_status, phase = {
            "cleared":  ("building", "build"),       # gate-1 approved → build begins
            "shipped":  ("waiting", "verify"),       # gate-2 approved + merged → awaiting operator test
            "merged":   ("merged", "done"),          # gate-3 VERIFIED works → truly done
            "rejected": ("rejected", "rejected"),
        }.get(a.status, ("", ""))
        if run_status:
            bridge.report_run(a.iid, status=run_status, phase=phase)
        print(out)
    elif a.cmd == "autoapprove":
        # Gate-2 (validate) AUTO-APPROVAL on green validation — the two-token carve-out.
        # The dashboard permits the service token to approve gate 2 ONLY (403 for gate 1/3),
        # recorded as decided_by='auto'. The loop then merges + pushes release + opens Gate 3.
        print(bridge.decide(a.iid, "approve", a.note))
    elif a.cmd == "close":
        # close the loop — only after the operator verifies the shipped change works
        from engine import github_connector as gh
        iid = str(a.iid)
        # Resolve BOTH the issue number and the repo from the item's state file — the id
        # suffix is not reliably the issue number for multi-repo slugged ids, and a
        # non-numeric suffix would crash int().
        repo, num = None, None
        sid = iid[3:] if iid.startswith("ev-") else iid
        sd = os.path.join(os.path.expanduser(os.getenv("EVOLVE_STATE_DIR") or "~/.evolve/runs"), sid, "state.json")
        try:
            with open(sd) as _f:
                _st = json.load(_f)
            repo = _st.get("repo") or None
            src = _st.get("source") or ""
            if src.startswith("github:") and "#" in src:
                num = int(src.split("#", 1)[1])
        except Exception:
            pass
        if num is None:
            tail = iid.split("-")[-1]
            if not tail.isdigit():
                raise SystemExit(f"cannot resolve an issue number for {iid!r} "
                                 "(no state-file source, non-numeric id suffix)")
            num = int(tail)
        print(gh.close_issue(num, comment=a.comment, repo=repo))
    elif a.cmd == "flush":
        n = len(open(bridge._OUTBOX).read().splitlines()) if os.path.exists(bridge._OUTBOX) else 0
        bridge._flush()
        left = len(open(bridge._OUTBOX).read().splitlines()) if os.path.exists(bridge._OUTBOX) else 0
        print(json.dumps({"buffered": n, "remaining": left, "sent": n - left}))


if __name__ == "__main__":
    main()
