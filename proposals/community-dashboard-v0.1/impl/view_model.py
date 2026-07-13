"""Read-only normalization for the community dashboard.

Inputs are derived authority views only. This module never scans wake/run logs.
"""
from __future__ import annotations

import html
from typing import Any

ALLOWED_SOURCES = (
    "memory-recall:projection", "governance-show", "prospective-show", "control-heads",
    "peer-chat:formal-channel", "frame-ledger:closed-continuation",
)


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _snapshot_alive(snapshot: dict[str, Any]) -> bool:
    if snapshot.get("exists") is False or snapshot.get("fresh") is False:
        return False
    return str(snapshot.get("state", "active")).lower() not in {"withdrawn", "expired", "superseded", "dormant", "retired", "missing", "stale"}


def _source_verified(ref: Any, alive_refs: set[Any], recall_fresh: bool) -> bool:
    """Verify each source class through the authority that can adjudicate it."""
    if ref in alive_refs:
        return True
    return recall_fresh and str(ref).startswith("frame:")


def normalize_dashboard(
    recall: dict[str, Any], governance: dict[str, Any], prospective: dict[str, Any],
    control_heads: dict[str, Any], *, chat: list[dict[str, Any]] | None = None,
    receipts: list[dict[str, Any]] | None = None,
    governance_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Converge command outputs into a safe, source-carrying view model."""
    projection = recall.get("projection") or {}
    snapshots = projection.get("source_snapshots") or []
    alive_refs = {s.get("ref") for s in snapshots if s.get("ref") and _snapshot_alive(s)}
    dirty_refs = {s.get("ref") for s in snapshots if s.get("ref") and not _snapshot_alive(s)}
    recall_fresh = (recall.get("freshness") or {}).get("fresh") is True
    projection_sources = list(projection.get("sources") or [])
    projection_valid = bool(projection_sources) and all(
        _source_verified(ref, alive_refs, recall_fresh) for ref in projection_sources
    )
    as_of = projection.get("generated_at_utc")
    raw_agenda = prospective.get("open_agenda") or prospective.get("goals") or []
    if isinstance(raw_agenda, dict):
        raw_agenda = list(raw_agenda.values())
    agenda = []
    for item in raw_agenda:
        if not isinstance(item, dict):
            continue
        if str(item.get("state", "ACTIVE")).upper() != "ACTIVE":
            continue
        refs = list(item.get("sources") or ([item["source"]] if item.get("source") else []))
        # Ref-less entries retain the existing contract. Memory refs require a
        # live snapshot; frame refs are adjudicated by a fresh recall.
        valid = not refs or all(_source_verified(ref, alive_refs, recall_fresh) for ref in refs)
        agenda.append({**item, "valid": valid, "unverifiable": bool(refs) and not valid, "source_refs": refs})
    raw_proposals = governance.get("proposals") or governance.get("targets") or []
    if isinstance(raw_proposals, dict):
        raw_proposals = list(raw_proposals.values())
    proposals = []
    for item in raw_proposals:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "historical")).lower()
        proposals.append({**item, "valid": state in {"active", "proposed", "approved"}, "source_refs": item.get("sources", [])})
    activation = recall.get("activation") or {}
    control_head_refs = [ref for ref in control_heads.values() if isinstance(ref, str) and ref]
    control_heads_valid = recall_fresh
    verifiable = bool(as_of) and recall_fresh and projection_valid and control_heads_valid
    return {
        "as_of": as_of,
        "verifiable": verifiable,
        "authority": {"state": activation.get("state", "UNKNOWN"), "continuation_allowed": bool(activation.get("continuation_allowed")), "control_heads": control_heads, "source_refs": control_head_refs, "valid": control_heads_valid, "unverifiable": not control_heads_valid},
        "projection": ({"status": projection.get("status"), "focus": projection.get("focus"), "next_action": projection.get("next_action"), "source_refs": projection_sources, "valid": True} if projection_valid else {"valid": False, "label": "已失效/脏", "source_refs": projection_sources}),
        "governance": proposals,
        "agenda": agenda,
        "chat": list(chat or []),
        "recent_receipts": list(receipts or []),
        "discussion": list(governance_items or []),
        "source_health": {"alive": sorted(alive_refs), "dirty": sorted(dirty_refs)},
        "data_sources": list(ALLOWED_SOURCES),
    }


def render_authority_text(vm: dict[str, Any]) -> str:
    state = escape(vm["authority"]["state"])
    proj = vm["projection"]
    projection_text = escape(proj.get("focus", proj.get("label", "无有效投影")))
    rows = [f"<p><strong>激活状态：{state}</strong></p>", f"<p>当前投影：{projection_text}</p>"]
    for item in vm["governance"]:
        label = "valid" if item.get("valid") else "历史"
        rows.append(f"<li>{escape(label)} — {escape(item.get('summary', item.get('description', '治理条目')))}</li>")
    return "\n".join(rows)
