import json

import pandas as pd
import streamlit as st

from src.core.store import read_events
from src.ui.theme import page_head
from src.ui.common import context, render_evidence, get_scope

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]

page_head("Governance", "Audit trail & traceability", "Append-only log of every AI output and PM decision, with a full trace from each requirement back to the raw customer verbatims.")

tab_trace, tab_log, tab_export = st.tabs(["Trace a requirement", "Event log", "Export"])

with tab_trace:
    if not ws["requirements"]:
        st.info("No requirements yet.")
    else:
        rid = st.selectbox("Requirement", [r["id"] for r in ws["requirements"]],
                           format_func=lambda i: next(f"{r['id']} · {r['title']} ({r['status']})" for r in ws["requirements"] if r["id"] == i))
        r = next(x for x in ws["requirements"] if x["id"] == rid)
        st.markdown(f"### {r['id']} · {r['title']}\n> {r['statement']}")
        st.markdown(f"**Status:** `{r['status']}` · **PM rationale:** {r.get('pm_note') or '–'}")

        st.markdown("#### ⬆️ Derived from insights")
        for iid in r["linked_insight_ids"]:
            ins = next((i for i in ws["insights"] if i["id"] == iid), None)
            if ins:
                st.markdown(f"- **{iid} · {ins['title']}** — status `{ins['status']}`, PM note: {ins.get('pm_note') or '–'}")
            else:
                st.markdown(f"- {iid} — ⚠️ not found in current insight set")

        st.markdown("#### 📎 Evidence")
        render_evidence(r["evidence"])

        st.markdown("#### 🗣️ Raw verbatims behind the cited feedback")
        ids = [e["ref"] for e in r["evidence"] if e["source_type"] == "feedback"]
        raw = ctx["comments"][ctx["comments"]["id"].isin(ids)]
        st.dataframe(raw, hide_index=True, width="stretch")

        st.markdown("#### 🕓 Decision history")
        ev = read_events(ws["key"], rid)
        if ev:
            st.dataframe(pd.DataFrame(ev)[["ts", "actor", "action", "rationale", "before", "after"]], hide_index=True, width="stretch")
        else:
            st.caption("No events for this requirement yet.")

with tab_log:
    events = read_events(ws["key"])
    st.caption(f"{len(events)} events for workspace `{ws['key']}`")
    if events:
        df = pd.DataFrame(events)
        actor = st.multiselect("Actor", sorted(df["actor"].unique()), default=sorted(df["actor"].unique()))
        df = df[df["actor"].isin(actor)]
        st.dataframe(df[["ts", "actor", "action", "entity_type", "entity_id", "rationale"]].iloc[::-1], hide_index=True, width="stretch")

with tab_export:
    st.download_button("Download workspace (JSON)", json.dumps(ws, indent=2, ensure_ascii=False),
                       file_name=f"{ws['key']}_workspace.json", mime="application/json")
    st.download_button("Download audit log (JSONL)", "\n".join(json.dumps(e, ensure_ascii=False) for e in read_events(ws["key"])),
                       file_name=f"{ws['key']}_audit.jsonl", mime="application/json")
    lines = [f"# Requirement set — {ws['key']}", ""]
    for r in ws["requirements"]:
        lines += [f"## {r['id']} · {r['title']} — {r['status'].upper()}", f"> {r['statement']}", "",
                  f"- Customer value: {r['customer_value']}", f"- Markets: {', '.join(r['target_markets'])}",
                  f"- Confidence: {r['confidence']}", f"- PM rationale: {r.get('pm_note') or '–'}",
                  "- Assumptions: " + "; ".join(r["assumptions"]), "- Uncertainties: " + "; ".join(r["uncertainties"]),
                  "- Evidence: " + "; ".join(f"{e['ref']} ({e.get('verification', '')})" for e in r["evidence"]), ""]
    st.download_button("Download requirement report (Markdown)", "\n".join(lines), file_name=f"{ws['key']}_requirements.md")
