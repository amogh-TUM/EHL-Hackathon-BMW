import json

import pandas as pd
import streamlit as st

from src.core.store import read_events
from src.core.config import SALES_FILE, STUDY_FILE, VEHICLES
from src.ui.common import context, get_scope, render_evidence
from src.ui.theme import e, page_head

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]

cfg = VEHICLES[vehicle]
comments, cls, study = ctx["comments"], ctx["cls"], ctx["study"]

page_head("Governance", "Trace", "Every requirement traced back to raw customer verbatims; every AI output and PM decision in an append-only log.")

tab_trace, tab_change, tab_log, tab_src, tab_export = st.tabs(["Trace a requirement", "Change log", "Event log", "Sources", "Export"])

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

with tab_change:
    st.caption("What changed and why: AI self-review suggestions, adopted suggestions, PM edits, weight changes and re-runs.")
    CHANGE_ACTIONS = {"suggest_revision": "AI suggested new wording", "adopt_ai_suggestion": "PM adopted AI wording",
                      "requirement_modified": "PM modified requirement", "set_weights": "PM changed weights",
                      "regenerate_insights": "Insights re-run", "regenerate_requirements": "Requirements re-drafted"}
    changes = [ev for ev in read_events(ws["key"]) if ev["action"] in CHANGE_ACTIONS]
    if not changes:
        st.caption("No changes yet.")
    for ev in reversed(changes):
        with st.container(border=True):
            st.markdown(f"**{CHANGE_ACTIONS[ev['action']]}** · `{ev['entity_id']}` · {ev['ts']} · by {ev['actor']}")
            b, a_ = ev.get("before"), ev.get("after")
            if isinstance(b, dict):
                b = b.get("statement", b)
            if isinstance(a_, dict):
                a_ = a_.get("statement", a_)
            if b or a_:
                c1, c2 = st.columns(2)
                c1.markdown(f"<small>BEFORE</small><br>{e(b)}", unsafe_allow_html=True)
                c2.markdown(f"<small>AFTER</small><br>{e(a_)}", unsafe_allow_html=True)
            if ev.get("rationale"):
                st.caption(f"Reason: {ev['rationale']}")

with tab_log:
    events = read_events(ws["key"])
    st.caption(f"{len(events)} events for workspace `{ws['key']}`")
    if events:
        df = pd.DataFrame(events)
        actor = st.multiselect("Actor", sorted(df["actor"].unique()), default=sorted(df["actor"].unique()))
        df = df[df["actor"].isin(actor)]
        st.dataframe(df[["ts", "actor", "action", "entity_type", "entity_id", "rationale"]].iloc[::-1], hide_index=True, width="stretch")

with tab_src:
    by_market = comments["market"].value_counts()
    mk = " · ".join(f"{m}: {int(by_market.get(m, 0)):,}" for m in ["EU", "US", "CN", "RoW"])
    study_markets = ", ".join(sorted(set(study["market"]))) or "none"
    sources = [
        ("BMW feedback workbook", cfg["feedback"],
         f"{len(cls):,} classification rows / {len(comments):,} distinct feedback IDs ({mk}). Records can carry several classifications. "
         "Every AI citation is verified against this file.", "Integrated · customer feedback", None),
        ("BMW customer study", STUDY_FILE,
         f"2025 satisfaction study: CN/EU mean scores (1-10) and US rating distributions (7-point). Available for this line in: {study_markets}. "
         "Different questionnaires per region — compare within a market.", "Integrated · customer study", None),
        ("Sales workbook", SALES_FILE, "Volumes by market for 2024, 2025 and the 2030 forecast; used for the market-volume factor.",
         "Integrated · planning context", None),
        ("BMW option list", cfg["options"], "Germany-market price and equipment list (2026). Used to check what is already offered. "
         "Configuration context only — not proof of availability elsewhere or of an unmet need.", "Integrated · DE context", None),
        ("Hackathon brief", "BMW_Hackathon_Briefing_Short.pdf", "Mission and scope of the challenge; reflected in the PM workflow.",
         "Reference", None),
    ]
    web = []
    for r in ws["requirements"]:
        for res in r.get("web_research", []):
            for s in res["sources"]:
                web.append(("Web research · external", s["title"], f"Collected for {r['id']} ({r['title']}). External context — verify before relying on it.",
                            "Open ↗", s["url"]))


    def card(kind, name, detail, status, url):
        tag = (f'<a class="source-status" href="{e(url)}" target="_blank" rel="noopener">{e(status)}</a>' if url
               else f'<span class="source-status">{e(status)}</span>')
        return (f'<div class="source-card"><div class="source-kind">{e(kind)}</div><div><div class="source-name">{e(name)}</div>'
                f'<div class="source-detail">{e(detail)}</div></div>{tag}</div>')


    with st.container(border=True):
        st.html("".join(card(*s) for s in sources))
    with st.container(border=True):
        st.markdown(f"### External knowledge ({len(web)})")
        st.caption("Capability and market context from web research — not customer evidence.")
        if web:
            st.html("".join(card(*s) for s in web))
        else:
            st.caption("No web research yet — use “Research competitors & trends” on a requirement.")

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
