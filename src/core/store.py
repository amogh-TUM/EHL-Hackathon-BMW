"""Workspace persistence and the append-only audit trail."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .config import AUDIT_LOG, WORKSPACE

STATUSES = ["proposed", "approved", "modified", "postponed", "rejected"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def workspace_key(vehicle: str, markets: list[str]) -> str:
    return f"{vehicle}_{'-'.join(sorted(markets))}"


def load_workspace(key: str) -> dict:
    p = WORKSPACE / f"{key}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"key": key, "insights": [], "insight_caveats": [], "requirements": [], "weights": None, "runs": []}


def save_workspace(ws: dict) -> None:
    p = WORKSPACE / f"{ws['key']}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(ws, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def log_event(workspace: str, actor: str, action: str, entity_type: str, entity_id: str,
              before=None, after=None, rationale: str = "", meta: dict | None = None) -> dict:
    """Append one immutable event. Never rewritten - the history is reconstructable from this file."""
    event = {"event_id": uuid.uuid4().hex[:12], "ts": _now(), "workspace": workspace, "actor": actor,
             "action": action, "entity_type": entity_type, "entity_id": entity_id,
             "before": before, "after": after, "rationale": rationale, "meta": meta or {}}
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_events(workspace: str | None = None, entity_id: str | None = None) -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    events = [json.loads(line) for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    if workspace:
        events = [e for e in events if e["workspace"] == workspace]
    if entity_id:
        events = [e for e in events if e["entity_id"] == entity_id]
    return events
