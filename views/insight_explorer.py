import streamlit as st

from src.core.store import log_event, save_workspace
from src.ui import evidence_panels
from src.ui.actions import run_analysis, run_draft_and_check
from src.ui.common import ai_ready, context, gaps_box, get_scope, meter_counts, render_evidence, step_states
from src.ui.theme import e, evidence_meter, page_head, pill, stepper

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]

page_head("Steps 1-2 · Signal engine + Gate 1", "Insight Explorer",
          "What are customers telling us? The AI proposes insights with verified citations — you keep the ones that matter.")
stepper(step_states(ws))
gaps_box(ctx["gaps"])

INSIGHT_REJECT_REASONS = ["Not relevant for successor", "Evidence too thin", "Duplicate insight", "Wrong market", "Not customer value"]

tab_ins, tab_ev = st.tabs(["Insights · Gate 1", "Evidence room (raw data)"])

with tab_ins:
    c1, c2 = st.columns([3, 1])
    if not ws["insights"]:
        c1.info("Step 1 — let the AI analyse the feedback, customer study and sales data for this scope (~2 min).")
    if c2.button("▶ Run analysis" if not ws["insights"] else "↻ Re-run analysis", type="primary" if not ws["insights"] else "secondary",
                 disabled=not ai_ready(), width="stretch"):
        if run_analysis(ctx, vehicle, markets):
            st.rerun()

    if ws["insights"]:
        n_acc = sum(i["status"] == "accepted" for i in ws["insights"])
        n_open = sum(i["status"] == "proposed" for i in ws["insights"])
        b1, b2, b3 = st.columns([2, 1.3, 1.5])
        b1.markdown(f"**{n_acc} accepted · {n_open} open · {len(ws['insights']) - n_acc - n_open} rejected**")
        strong = [i for i in ws["insights"] if i["status"] == "proposed" and i["evidence_basis"] == "evidence_based"
                  and not any(str(x.get("verification", "")).startswith("unverified") for x in i["evidence"])]
        if b2.button(f"Accept all evidence-based ({len(strong)})", disabled=not strong, width="stretch"):
            for i in strong:
                i["status"], i["pm_note"] = "accepted", "Bulk-accepted: evidence-based, all citations verified"
                log_event(ws["key"], "PM", "insight_accepted", "insight", i["id"], before="proposed", after="accepted",
                          rationale=i["pm_note"])
            save_workspace(ws)
            st.rerun()
        if b3.button("Continue → draft & self-check ▶", type="primary", disabled=n_acc == 0 or not ai_ready(), width="stretch",
                     help="Runs the synthesis and evaluation engines on your accepted insights"):
            if run_draft_and_check(ctx, vehicle):
                st.switch_page("views/board.py")
        if ws.get("insight_caveats"):
            with st.expander("AI caveats on this analysis"):
                for c in ws["insight_caveats"]:
                    st.markdown(f"- {c}")

        BASIS = {"evidence_based": ("evidence-based", "accepted"), "mixed": ("mixed", "warn"), "assumption_based": ("assumption-based", "rejected")}
        cols = st.columns(2, gap="small")
        for n, ins in enumerate(ws["insights"]):
            with cols[n % 2].container(border=True):
                basis, cls_ = BASIS.get(ins["evidence_basis"], (ins["evidence_basis"], ""))
                st.html(f'<div class="req-title">{e(ins["id"])} · {e(ins["title"])}</div>'
                        f'<div class="req-sub">{e(ins["description"])}</div>'
                        f'<div>{pill(ins["status"], ins["status"])}{pill(basis, cls_)}{pill(ins["insight_type"].replace("_", " "))}'
                        f'{pill(" · ".join(ins["markets"]))}</div>'
                        + evidence_meter(*meter_counts({"evidence": ins["evidence"], "assumptions": []})))
                with st.expander(f"Evidence & conflicts ({len(ins['evidence'])})"):
                    render_evidence(ins["evidence"])
                    for c in ins["conflicting_signals"]:
                        st.markdown(f"- ⚔️ {c}")
                    for g in ins["data_gaps"]:
                        st.markdown(f"- 🕳️ {g}")
                if ins["status"] == "proposed":
                    a1, a2 = st.columns(2)
                    if a1.button("✓ Accept", key=f"acc_{ins['id']}", type="primary", width="stretch"):
                        ins["status"], ins["pm_note"] = "accepted", ins.get("pm_note", "")
                        save_workspace(ws)
                        log_event(ws["key"], "PM", "insight_accepted", "insight", ins["id"], before="proposed", after="accepted")
                        st.rerun()
                    with a2.popover("✕ Reject", width="stretch"):
                        why = st.pills("Why?", INSIGHT_REJECT_REASONS, selection_mode="multi", key=f"why_{ins['id']}")
                        note = st.text_input("Note (optional)", key=f"note_{ins['id']}")
                        if st.button("Confirm reject", key=f"rej_{ins['id']}", disabled=not (why or note.strip())):
                            ins["status"], ins["pm_note"] = "rejected", "; ".join([*why, note.strip()]).strip("; ")
                            save_workspace(ws)
                            log_event(ws["key"], "PM", "insight_rejected", "insight", ins["id"], before="proposed",
                                      after="rejected", rationale=ins["pm_note"])
                            st.rerun()
                else:
                    u1, u2 = st.columns([3, 1])
                    u1.caption(f"PM note: {ins.get('pm_note') or '–'}")
                    if u2.button("Undo", key=f"undo_{ins['id']}"):
                        before = ins["status"]
                        ins["status"] = "proposed"
                        save_workspace(ws)
                        log_event(ws["key"], "PM", "insight_reopened", "insight", ins["id"], before=before, after="proposed")
                        st.rerun()

with tab_ev:
    evidence_panels.render(ctx, vehicle, markets)
