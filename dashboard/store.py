"""SQLite store for the Evolve dashboard.

stdlib sqlite3 only, cross-platform (no unix-only assumptions). Tables are created
if-not-exists on startup. Upserts MERGE: a null/omitted field never clobbers an
existing column value (COALESCE on every nullable column).

Schema:
  run(instance_id PK, repo, title, source, phase, status, current_agent,
      current_node, archived INTEGER DEFAULT 0, cost_usd REAL DEFAULT 0, updated_at)
  gate_queue(instance_id PK, repo, gate, title, rec_action, rec_why, packet,
      status, decision, decided_by, note, decided_at, updated_at)   # packet = JSON text
  activity(id INTEGER PK AUTOINCREMENT, instance_id, agent, kind, message, ts)
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone


def _now() -> str:
    """Timezone-aware ISO-8601 UTC timestamp (never a bare naive datetime)."""
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: str):
        self.db_path = os.path.expanduser(db_path)
        d = os.path.dirname(self.db_path)
        if d:
            os.makedirs(d, exist_ok=True)
        # check_same_thread=False so a single connection can serve the (threaded)
        # ASGI server; we guard every write with a lock for safety.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS run (
                    instance_id   TEXT PRIMARY KEY,
                    repo          TEXT,
                    title         TEXT,
                    source        TEXT,
                    phase         TEXT,
                    status        TEXT,
                    current_agent TEXT,
                    current_node  TEXT,
                    archived      INTEGER DEFAULT 0,
                    cost_usd      REAL DEFAULT 0,
                    updated_at    TEXT
                );
                CREATE TABLE IF NOT EXISTS gate_queue (
                    instance_id TEXT PRIMARY KEY,
                    repo        TEXT,
                    gate        TEXT,
                    title       TEXT,
                    rec_action  TEXT,
                    rec_why     TEXT,
                    packet      TEXT,
                    status      TEXT,
                    decision    TEXT,
                    decided_by  TEXT,
                    note        TEXT,
                    decided_at  TEXT,
                    updated_at  TEXT
                );
                CREATE TABLE IF NOT EXISTS activity (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT,
                    agent       TEXT,
                    kind        TEXT,
                    message     TEXT,
                    ts          TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_activity_instance
                    ON activity(instance_id, id);
                CREATE TABLE IF NOT EXISTS issue_allowlist (
                    repo      TEXT,
                    number    INTEGER,
                    added_by  TEXT,
                    added_at  TEXT,
                    PRIMARY KEY (repo, number)
                );
                """
            )

    # ----------------------------------------------------- issue allowlist ---
    def admit_issue(self, repo: str, number: int, added_by: str = "") -> None:
        """Admit a GitHub issue for processing (manual-intake repos). Idempotent."""
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO issue_allowlist (repo, number, added_by, added_at) "
                "VALUES (?, ?, ?, ?)", (repo, int(number), added_by, _now()))

    def revoke_issue(self, repo: str, number: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM issue_allowlist WHERE repo = ? AND number = ?", (repo, int(number)))

    def list_admitted(self, repo: str | None = None) -> list[dict]:
        q, args = "SELECT repo, number, added_at FROM issue_allowlist", []
        if repo:
            q += " WHERE repo = ?"
            args.append(repo)
        q += " ORDER BY number"
        with self._lock:
            return [dict(r) for r in self._conn.execute(q, args).fetchall()]

    # ----------------------------------------------------------------- runs ---
    def upsert_run(self, instance_id: str, *, repo=None, title=None, source=None,
                   phase=None, status=None, current_agent=None, current_node=None,
                   cost_usd=None, archived=None) -> None:
        """Insert or MERGE a run. Omitted/None fields keep the existing value
        (COALESCE of the new value over the stored column)."""
        if not instance_id:
            raise ValueError("instance_id is required")
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO run (instance_id, repo, title, source, phase, status,
                                 current_agent, current_node, cost_usd, archived,
                                 updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                        COALESCE(?, 0), COALESCE(?, 0), ?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    -- NULLIF(..., '') so an EMPTY-STRING field (report_run defaults every text
                    -- field to "") is treated as "no update" and preserves the stored value —
                    -- otherwise a partial report (status/events only) blanks phase/title/etc.
                    repo          = COALESCE(NULLIF(excluded.repo, ''),          run.repo),
                    title         = COALESCE(NULLIF(excluded.title, ''),         run.title),
                    source        = COALESCE(NULLIF(excluded.source, ''),        run.source),
                    phase         = COALESCE(NULLIF(excluded.phase, ''),         run.phase),
                    status        = COALESCE(NULLIF(excluded.status, ''),        run.status),
                    current_agent = COALESCE(NULLIF(excluded.current_agent, ''), run.current_agent),
                    current_node  = COALESCE(NULLIF(excluded.current_node, ''),  run.current_node),
                    cost_usd      = COALESCE(?,                       run.cost_usd),
                    archived      = COALESCE(?,                       run.archived),
                    updated_at    = excluded.updated_at
                """,
                (instance_id, repo, title, source, phase, status, current_agent,
                 current_node, cost_usd, archived, _now(), cost_usd, archived),
            )

    def list_runs(self, *, archived: bool = False, repo: str | None = None) -> list[dict]:
        q = "SELECT * FROM run"
        clauses, args = [], []
        # active view = only non-archived; archived view = ONLY archived (distinct lists, not a superset)
        clauses.append("COALESCE(archived, 0) = " + ("1" if archived else "0"))
        if repo:
            clauses.append("repo = ?")
            args.append(repo)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY updated_at DESC, instance_id DESC"
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, instance_id: str) -> dict | None:
        with self._lock:
            r = self._conn.execute(
                "SELECT * FROM run WHERE instance_id = ?", (instance_id,)
            ).fetchone()
        return dict(r) if r else None

    def set_archived(self, instance_id: str, archived: bool) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE run SET archived = ?, updated_at = ? WHERE instance_id = ?",
                (1 if archived else 0, _now(), instance_id),
            )

    def cost_summary(self, *, repo: str | None = None) -> dict:
        q = "SELECT COUNT(*) AS runs, COALESCE(SUM(cost_usd), 0) AS total_usd FROM run"
        args: list = []
        if repo:
            q += " WHERE repo = ?"
            args.append(repo)
        with self._lock:
            r = self._conn.execute(q, args).fetchone()
        return {"runs": r["runs"], "total_usd": round(r["total_usd"] or 0.0, 4)}

    # ----------------------------------------------------------- activity ---
    def add_events(self, instance_id: str, events: list[dict]) -> int:
        """Append activity events. Returns the count appended."""
        n = 0
        with self._lock, self._conn:
            for ev in events or []:
                self._conn.execute(
                    "INSERT INTO activity (instance_id, agent, kind, message, ts) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (instance_id, ev.get("agent", ""), ev.get("kind", ""),
                     ev.get("message", ""), ev.get("ts") or _now()),
                )
                n += 1
        return n

    def events(self, instance_id: str, *, since: int = 0) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, agent, kind, message, ts FROM activity "
                "WHERE instance_id = ? AND id > ? ORDER BY id ASC",
                (instance_id, since or 0),
            ).fetchall()
        return [dict(r) for r in rows]

    # ----------------------------------------------------------------- gates ---
    def upsert_gate(self, instance_id: str, *, gate=None, repo=None, title=None,
                    rec_action=None, rec_why=None, packet=None, reset=False) -> None:
        """Insert or MERGE a gate row. packet is a dict (JSON-serialised) or None to
        keep the existing packet.

        DECISION SAFETY: a re-push of the SAME gate kind (an outbox replay, a
        stranded-item resume re-posting its packet) must never erase a decision the
        operator already recorded — the loop would then read 'waiting' and re-park an
        item the operator believes they approved. So a 'decided' row is preserved
        unless (a) the incoming gate KIND differs (the item advanced to its next
        gate — a fresh decision is genuinely owed) or (b) reset=True (an explicit
        re-open, e.g. the reverify endpoint)."""
        if not instance_id:
            raise ValueError("instance_id is required")
        packet_json = json.dumps(packet) if packet is not None else None
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT gate, status FROM gate_queue WHERE instance_id = ?",
                (instance_id,)).fetchone()
            if (row and not reset and row["status"] == "decided"
                    and (gate is None or gate == row["gate"])):
                # same-gate re-push after a decision: merge metadata, keep the decision
                self._conn.execute(
                    """
                    UPDATE gate_queue SET
                        repo       = COALESCE(?, repo),
                        title      = COALESCE(?, title),
                        rec_action = COALESCE(?, rec_action),
                        rec_why    = COALESCE(?, rec_why),
                        packet     = COALESCE(?, packet),
                        updated_at = ?
                    WHERE instance_id = ?
                    """,
                    (repo, title, rec_action, rec_why, packet_json, _now(), instance_id),
                )
                return
            self._conn.execute(
                """
                INSERT INTO gate_queue (instance_id, repo, gate, title, rec_action,
                                        rec_why, packet, status, decision, decided_by,
                                        note, decided_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting', NULL, NULL, NULL, NULL, ?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    repo       = COALESCE(excluded.repo,       gate_queue.repo),
                    gate       = COALESCE(excluded.gate,       gate_queue.gate),
                    title      = COALESCE(excluded.title,      gate_queue.title),
                    rec_action = COALESCE(excluded.rec_action, gate_queue.rec_action),
                    rec_why    = COALESCE(excluded.rec_why,    gate_queue.rec_why),
                    packet     = COALESCE(excluded.packet,     gate_queue.packet),
                    status     = 'waiting',
                    decision   = NULL,
                    decided_by = NULL,
                    note       = NULL,
                    decided_at = NULL,
                    updated_at = excluded.updated_at
                """,
                (instance_id, repo, gate, title, rec_action, rec_why, packet_json, _now()),
            )

    def _row_to_gate(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        if d.get("packet"):
            try:
                d["packet"] = json.loads(d["packet"])
            except (TypeError, ValueError):
                pass
        return d

    def list_gates(self, *, status: str | None = None, repo: str | None = None) -> list[dict]:
        q = "SELECT * FROM gate_queue"
        clauses, args = [], []
        if status:
            clauses.append("status = ?")
            args.append(status)
        if repo:
            clauses.append("repo = ?")
            args.append(repo)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY updated_at DESC, instance_id DESC"
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [self._row_to_gate(r) for r in rows]

    def get_gate(self, instance_id: str) -> dict | None:
        with self._lock:
            r = self._conn.execute(
                "SELECT * FROM gate_queue WHERE instance_id = ?", (instance_id,)
            ).fetchone()
        return self._row_to_gate(r) if r else None

    def record_decision(self, instance_id: str, *, decision: str, note: str = "",
                        decided_by: str = "") -> bool:
        """Record an operator decision and set status='decided'. Returns False if no
        such gate row exists."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE gate_queue SET decision = ?, note = ?, decided_by = ?, "
                "status = 'decided', decided_at = ?, updated_at = ? "
                "WHERE instance_id = ?",
                (decision, note, decided_by, _now(), _now(), instance_id),
            )
            return cur.rowcount > 0

    def resolve_gate(self, instance_id: str, status: str) -> bool:
        """Mark a gate resolved (clear from queue) after the engine acted. Returns
        False if no such gate row exists."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE gate_queue SET status = ?, updated_at = ? WHERE instance_id = ?",
                (status or "resolved", _now(), instance_id),
            )
            return cur.rowcount > 0
