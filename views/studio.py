from datetime import datetime, timezone

import streamlit as st

from src.core import llm, pipeline
from src.core.scoring import FACTORS
from src.core.store import log_event, save_workspace
from src.ui.common import (REASONS, ai_ready, context, get_scope, meter_counts, ranked_requirements, render_evidence,
                           step_states)
from src.ui.theme import callout, e, evidence_meter, page_head, pill, stepper

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]
reqs = ws["requirements"]

page_head("Step 4 · Gate 2", "Decision Studio",
          "One requirement at a time: the evidence, the AI's own critique, and your decision with a reason in two clicks.")
stepper(step_states(ws))

if not reqs:
    st.info("No requirements yet — accept insights and run “Draft & self-check” first.")
    st.stop()

scored, sens = ranked_requirements(ws)
scored = scored.set_index("id")
by_id = {r["id"]: r for r in reqs}
show_all = st.toggle("Include already decided", value=False)
queue = [i for i in scored.index if show_all or by_id[i]["status"] == "proposed"]
focus = st.session_state.pop("studio_focus", None)
if focus in by_id:
    if focus not in queue:
        queue = list(scored.index)
    st.session_state["studio_idx"] = queue.index(focus)
if not queue:
    st.success("🎉 Every requirement has a PM decision. See the Requirement Board or export from the Audit Trail.")
    st.stop()

idx = min(st.session_state.get("studio_idx", 0), len(queue) - 1)
n1, n2, n3 = st.columns([1, 4, 1])
if n1.button("← Previous", disabled=idx == 0, width="stretch"):
    st.session_state["studio_idx"] = idx - 1
    st.rerun()
n2.html(f'<div style="text-align:center;font:600 1.1rem var(--display);letter-spacing:1px;padding-top:6px">'
        f'{idx + 1} OF {len(queue)} {"IN QUEUE" if not show_all else "REQUIREMENTS"}</div>')
if n3.button("Next →", disabled=idx >= len(queue) - 1, width="stretch"):
    st.session_state["studio_idx"] = idx + 1
    st.rerun()

r = by_id[queue[idx]]
row = scored.loc[r["id"]]
ev = r.get("evaluation") or {}
left, right = st.columns([1.6, 1], gap="medium")

with left:
    with st.container(border=True):
        flags = pill(r["status"], r["status"]) + pill(f"confidence {r['confidence']}", "warn" if r["confidence"] == "low" else "")
        flags += pill(r["kano_category"]) + pill(" · ".join(r["target_markets"]))
        if not bool(sens.loc[r["id"], "robust"]):
            flags += pill("rank depends on weights", "warn")
        st.html(f'<div style="display:flex;justify-content:space-between;gap:12px"><div>'
                f'<div class="bmw-kicker" style="color:var(--blue)">{e(r["id"])} · RANK #{int(row["rank"])}</div>'
                f'<h3 style="margin:4px 0 6px;font:600 1.5rem var(--display)">{e(r["title"])}</h3>{flags}</div>'
                f'<div class="freq"><b>{row["priority_score"]:.0f}</b><small>PRIORITY</small></div></div>'
                f'<div class="callout" style="font-size:.85rem;color:#17232e"><b>Requirement</b>{e(r["statement"])}</div>'
                f'<div class="req-sub"><b>Customer value:</b> {e(r["customer_value"])}</div>'
                f'<div class="req-sub" style="margin-top:6px"><b>Today:</b> {e(r["current_offer_note"])}</div>'
                f'<div style="margin-top:10px" class="req-sub"><b>Evidence vs assumption</b></div>'
                + evidence_meter(*meter_counts(r)))

    t_why, t_ev, t_unc, t_ai, t_more = st.tabs(["Why this score", "Evidence", "Assumptions & risks", "AI self-review", "Challenge · research · history"])
    with t_why:
        for k, j in r["ai"].items():
            st.markdown(f"- **{FACTORS[k]['label']}** · AI-judged · {j['score']}/5 — {j['justification']}")
        if ev:
            st.markdown(f"- **BMW brand fit** · AI-judged · {ev['brand_fit']['score']}/5 ({ev['brand_pillar'].replace('_', ' ')}) — {ev['brand_fit']['justification']}")
        c = r["computed"]
        st.markdown(f"- **Voice of customer** · computed · {c['voice_volume_raw']} unique comments on {', '.join(c['topics']) or '–'}")
        st.markdown(f"- **Market volume 2030** · computed · {c['market_volume']:.0%} of the line's EU+CN+US volume")
        st.markdown(f"- **Evidence strength** · computed · {c['evidence_strength']:.2f}")
    with t_ev:
        render_evidence(r["evidence"])
    with t_unc:
        for title, items, icon in [("Forward-looking assumptions", r["assumptions"], "💭"), ("Uncertainties", r["uncertainties"], "❓"),
                                   ("Conflicting evidence", r["conflicting_evidence"], "⚔️")]:
            st.markdown(f"**{title}**")
            for x in items or ["none stated"]:
                st.markdown(f"- {icon} {x}")
    with t_ai:
        if not ev:
            st.caption("Not evaluated yet — run the self-check on the Requirement Board.")
        else:
            st.markdown(f"**Verdict:** `{ev['verdict'].replace('_', ' ')}` · **evidence check:** `{ev['evidence_check'].replace('_', ' ')}`")
            for i in ev["issues"] or ["no issues found"]:
                st.markdown(f"- {i}")
            if ev["suggestion_changed"]:
                st.markdown(f"**Suggested wording** ({ev['suggestion_status']}): _{ev['suggested_statement']}_  \n{ev['change_reason']}")
    with t_more:
        a1, a2 = st.columns(2)
        if a1.button("😈 Devil's advocate", disabled=not ai_ready(), width="stretch"):
            with st.spinner("Stress-testing ..."):
                try:
                    pipeline.challenge(ws, r)
                    st.rerun()
                except llm.LLMError as err:
                    st.error(str(err))
        if a2.button("🌐 Research competitors & trends", disabled=not ai_ready(), width="stretch"):
            with st.spinner("Searching the web ..."):
                try:
                    pipeline.research(ws, r, vehicle, ctx["comments"], ctx["study"])
                    st.rerun()
                except llm.LLMError as err:
                    st.error(str(err))
        for ch in reversed(r["challenges"]):
            st.markdown(f"**Devil's advocate → {ch['recommendation'].upper()}**: {ch['recommendation_rationale']}")
            st.markdown("\n".join(f"- {x}" for x in ch["counter_arguments"] + [f"Missing: {m}" for m in ch["missing_evidence"]]))
        for res in reversed(r["web_research"]):
            st.markdown("**Web research** (external — verify before relying on it)")
            st.write(res["summary"])
            for s in res["sources"]:
                st.markdown(f"- 🌐 [{s['title']}]({s['url']})")
        for v in r["versions"]:
            st.caption(f"{v['ts']}: previous wording — {v['before']}")

with right:
    with st.container(border=True):
        st.markdown("### Your decision")
        if ev:
            tone = {"ready_for_decision": False, "revise_first": True, "needs_more_evidence": True}[ev["verdict"]]
            st.html(callout(f"AI self-review: {ev['verdict'].replace('_', ' ')}",
                            (ev["issues"][0] if ev["issues"] else "No issues found.") + (" Suggested wording available." if ev["suggestion_changed"] else ""),
                            warn=tone))
        key_stmt = f"stmt_{r['id']}"
        st.session_state.setdefault(key_stmt, r["statement"])
        if ev.get("suggestion_status") == "open" and st.button("✨ Use AI's suggested wording", width="stretch"):
            st.session_state[key_stmt] = ev["suggested_statement"]
        stmt = st.text_area("Requirement wording", key=key_stmt, height=130)
        decision = st.segmented_control("Decision", ["approved", "modified", "postponed", "rejected"],
                                        format_func=lambda s: {"approved": "✅ Approve", "modified": "✏️ Modify",
                                                               "postponed": "⏸ Postpone", "rejected": "🛑 Reject"}[s],
                                        key=f"dec_{r['id']}")
        reasons = st.pills("Why? (pick one or more)", REASONS.get(decision, []), selection_mode="multi",
                           key=f"rsn_{r['id']}_{decision}") if decision else []
        note = st.text_input("Add a note (optional)", key=f"note_{r['id']}")
        changed = stmt.strip() != r["statement"].strip()
        problem = None
        if not decision:
            problem = "Pick a decision."
        elif not (reasons or note.strip()):
            problem = "Pick at least one reason — every decision is logged."
        elif decision == "modified" and not changed:
            problem = "Edit the wording (or use the AI suggestion) to modify."
        elif decision != "modified" and changed:
            problem = "You edited the wording — choose ✏️ Modify to keep it."
        if problem:
            st.caption(problem)
        if st.button("Confirm decision & next →", type="primary", disabled=problem is not None, width="stretch"):
            rationale = "; ".join([*reasons, note.strip()]).strip("; ")
            before = {"status": r["status"], "statement": r["statement"]}
            if changed:
                r["versions"].append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "before": r["statement"]})
                r["statement"] = stmt.strip()
                if ev.get("suggestion_status") == "open" and stmt.strip() == ev["suggested_statement"].strip():
                    ev["suggestion_status"] = "adopted"
                    log_event(ws["key"], "PM", "adopt_ai_suggestion", "requirement", r["id"], before=before["statement"], after=r["statement"])
            elif ev.get("suggestion_status") == "open":
                ev["suggestion_status"] = "declined"
            r["status"], r["pm_note"] = decision, rationale
            save_workspace(ws)
            log_event(ws["key"], "PM", f"requirement_{decision}", "requirement", r["id"], before=before,
                      after={"status": decision, "statement": r["statement"], "score": float(row["priority_score"]),
                             "weights": ws.get("weights")}, rationale=rationale)
            st.session_state.pop(key_stmt, None)
            if not show_all:
                st.session_state["studio_idx"] = idx  # the next item slides into this position
            else:
                st.session_state["studio_idx"] = min(idx + 1, len(queue) - 1)
            st.toast(f"{r['id']} {decision} — logged")
            st.rerun()
    st.html(callout("Before approval", "Customer-facing? Actionable? Grounded in evidence that applies to the selected market? "
                    "AI-judged factors are inputs, not facts."))
