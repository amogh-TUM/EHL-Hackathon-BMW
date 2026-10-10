import streamlit as st

from src.core import llm, pipeline
from src.core.store import log_event, save_workspace
from src.ui.theme import page_head
from src.ui.common import context, gaps_box, render_evidence, get_scope

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]

page_head("Signal agent · Gate 1", "Customer insights", "AI proposes customer needs and pain points from the data. Accept or reject each one before requirements are derived; citations are machine-verified against the dataset.")
gaps_box(ctx["gaps"])

label = "Regenerate insights" if ws["insights"] else "Generate insights with AI"
if st.button(label, type="primary"):
    if ws["insights"]:
        log_event(ws["key"], "PM", "regenerate_insights", "insight_set", ws["key"], before=[i["id"] for i in ws["insights"]])
    with st.spinner("The AI is analysing feedback, study and sales data (this can take a minute) ..."):
        try:
            pipeline.run_insights(ws, vehicle, markets, ctx["comments"], ctx["cls"], ctx["study"], ctx["sales"], ctx["gaps"])
            st.rerun()
        except llm.LLMError as e:
            st.error(str(e))

if not ws["insights"]:
    st.info("No insights yet for this scope.")
    st.stop()

if ws.get("insight_caveats"):
    with st.expander("AI caveats on this analysis"):
        for c in ws["insight_caveats"]:
            st.markdown(f"- {c}")

flt = st.radio("Show", ["all", "proposed", "accepted", "rejected"], horizontal=True)
BASIS = {"evidence_based": "🟢 evidence-based", "mixed": "🟡 mixed", "assumption_based": "🟠 assumption-based"}

for ins in ws["insights"]:
    if flt != "all" and ins["status"] != flt:
        continue
    n_bad = sum(str(e.get("verification", "")).startswith("unverified") for e in ins["evidence"])
    with st.container(border=True):
        h1, h2 = st.columns([5, 2])
        h1.markdown(f"#### {ins['id']} · {ins['title']}")
        h2.markdown(f"**Status:** `{ins['status']}`  \n{BASIS.get(ins['evidence_basis'], ins['evidence_basis'])} · {ins['insight_type'].replace('_', ' ')}")
        st.write(ins["description"])
        st.caption(f"Markets: {', '.join(ins['markets'])} · VFC topics: {', '.join(ins['vfc_topics']) or '–'}")
        if n_bad:
            st.warning(f"{n_bad} citation(s) could not be verified against the dataset — treat with care.")
        with st.expander(f"Evidence ({len(ins['evidence'])})"):
            render_evidence(ins["evidence"])
        if ins["conflicting_signals"] or ins["data_gaps"]:
            with st.expander("Conflicts & data gaps"):
                for c in ins["conflicting_signals"]:
                    st.markdown(f"- ⚔️ {c}")
                for g in ins["data_gaps"]:
                    st.markdown(f"- 🕳️ {g}")

        note = st.text_input("PM note / rationale", value=ins.get("pm_note", ""), key=f"note_{ins['id']}")
        b1, b2, b3, _ = st.columns([1, 1, 1, 4])
        for btn, status, col in [("Accept", "accepted", b1), ("Reject", "rejected", b2), ("Reset", "proposed", b3)]:
            if col.button(btn, key=f"{status}_{ins['id']}", disabled=ins["status"] == status):
                if status == "rejected" and not note.strip():
                    st.error("A rationale is required to reject an insight.")
                else:
                    before = ins["status"]
                    ins["status"], ins["pm_note"] = status, note
                    save_workspace(ws)
                    log_event(ws["key"], "PM", f"insight_{status}", "insight", ins["id"], before=before, after=status, rationale=note)
                    st.rerun()
