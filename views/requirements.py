from datetime import datetime, timezone

import plotly.express as px
import streamlit as st

from src.core import llm, pipeline
from src.core.scoring import DEFAULT_WEIGHTS, FACTORS, PRESETS, factor_table, score, sensitivity
from src.core.store import STATUSES, log_event, save_workspace
from src.ui.theme import page_head
from src.ui.common import context, gaps_box, option_text, render_evidence, get_scope

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]

page_head("Product + priority agents · Gate 2", "Customer requirement proposals", "AI drafts requirements from accepted insights; the system scores them with your weights. Every proposal stays a draft until you decide it.")
gaps_box(ctx["gaps"])

n_acc = sum(i["status"] == "accepted" for i in ws["insights"])
c1, c2 = st.columns([3, 2])
c1.markdown(f"**{n_acc}** accepted insight(s) available as input.")
if c2.button("Regenerate requirements" if ws["requirements"] else "Generate requirements with AI",
             type="primary", disabled=n_acc == 0):
    if ws["requirements"]:
        log_event(ws["key"], "PM", "regenerate_requirements", "requirement_set", ws["key"],
                  before=[(r["id"], r["status"]) for r in ws["requirements"]])
    with st.spinner("The AI is drafting requirements and checking the current option list ..."):
        try:
            pipeline.run_requirements(ws, vehicle, ctx["comments"], ctx["cls"], ctx["study"], ctx["sales"], option_text(vehicle))
            st.rerun()
        except llm.LLMError as e:
            st.error(str(e))

reqs = ws["requirements"]
if not reqs:
    st.info("No requirements yet. Accept insights on the Insights page first, then generate.")
    st.stop()

# ---------- Prioritisation ----------
st.subheader("Prioritisation")
with st.expander("⚖️ Scoring weights (PM-owned)", expanded=False):
    preset = st.selectbox("Start from preset", list(PRESETS))
    base = PRESETS[preset] if preset != "Balanced (default)" else (ws.get("weights") or DEFAULT_WEIGHTS)
    cols = st.columns(3)
    weights = {}
    for i, (f, meta) in enumerate(FACTORS.items()):
        weights[f] = cols[i % 3].slider(f"{meta['label']} · *{meta['origin']}*", 0, 50, int(base[f]), help=meta["help"], key=f"w_{preset}_{f}")
    if st.button("Save weights"):
        log_event(ws["key"], "PM", "set_weights", "weights", ws["key"], before=ws.get("weights"), after=weights)
        ws["weights"] = weights
        save_workspace(ws)
        st.success("Weights saved and logged.")
    st.caption("Score = Σ (weight × normalised factor) / Σ weights × 100. AI-judged factors come with written justifications; computed factors are derived from the data.")

ft = factor_table(reqs)
scored = score(ft, weights)
sens = sensitivity(ft)
contrib = scored.melt(id_vars=["id", "title", "priority_score"], value_vars=[f"contrib_{f}" for f in FACTORS],
                      var_name="factor", value_name="points")
contrib["factor"] = contrib["factor"].str.replace("contrib_", "").map(lambda f: f"{FACTORS[f]['label']} ({FACTORS[f]['origin']})")
contrib["label"] = contrib["id"] + " · " + contrib["title"].str.slice(0, 45)
fig = px.bar(contrib, y="label", x="points", color="factor", orientation="h",
             category_orders={"label": (scored["id"] + " · " + scored["title"].str.slice(0, 45)).tolist()},
             height=120 + 38 * len(scored))
fig.update_layout(yaxis_title=None, xaxis_title="priority score (0-100)", legend_title=None, margin=dict(l=0, r=0, t=10, b=0),
                  legend=dict(orientation="h", y=-0.15))
st.plotly_chart(fig, width="stretch")

status_by_id = {r["id"]: r["status"] for r in reqs}
conf_by_id = {r["id"]: r["confidence"] for r in reqs}
table = scored[["rank", "id", "title", "priority_score"]].merge(
    sens[["best_rank", "worst_rank", "robust"]], left_on="id", right_index=True)
table["confidence"] = table["id"].map(conf_by_id)
table["status"] = table["id"].map(status_by_id)
st.dataframe(table, hide_index=True, width="stretch",
             column_config={"robust": st.column_config.CheckboxColumn("robust to weighting", help="Rank varies ≤2 places across all presets")})
st.caption("Best/worst rank = rank range across the weighting presets. Non-robust items depend on how you weigh the trade-offs — decide them deliberately.")

# ---------- Review ----------
st.subheader("Review & decide")
focus = st.session_state.get("focus_req")
if focus and any(r["id"] == focus for r in reqs):
    f1, f2 = st.columns([4, 1])
    f1.info(f"Showing {focus} from the decision queue.")
    if f2.button("Show all"):
        st.session_state.pop("focus_req", None)
        st.rerun()
else:
    focus = None
flt = st.radio("Show", ["all"] + STATUSES, horizontal=True, disabled=bool(focus))
order = scored["id"].tolist()
for r in sorted(reqs, key=lambda x: order.index(x["id"])):
    if focus and r["id"] != focus:
        continue
    if not focus and flt != "all" and r["status"] != flt:
        continue
    row = scored[scored["id"] == r["id"]].iloc[0]
    flags = []
    if r["confidence"] == "low":
        flags.append("🟠 low confidence")
    if r["computed"]["evidence_strength"] < 0.35:
        flags.append("🕳️ thin evidence")
    if any(str(e.get("verification", "")).startswith("unverified") for e in r["evidence"]):
        flags.append("❌ unverified citation(s)")
    if not bool(sens.loc[r["id"], "robust"]):
        flags.append("⚖️ rank sensitive to weights")
    with st.container(border=True):
        h1, h2 = st.columns([5, 2])
        h1.markdown(f"#### #{int(row['rank'])} · {r['id']} · {r['title']}")
        h2.markdown(f"**Score {row['priority_score']}** · `{r['status']}`  \n{r['kano_category']} · confidence {r['confidence']}")
        st.markdown(f"> {r['statement']}")
        if flags:
            st.markdown(" · ".join(flags))
        st.caption(f"Markets: {', '.join(r['target_markets'])} · from insights {', '.join(r['linked_insight_ids'])} · current offer: {r['current_offer_note']}")

        t1, t2, t3, t4, t5 = st.tabs(["Why", "Evidence", "Assumptions & uncertainty", "Challenge & research", "History"])
        with t1:
            st.markdown(f"**Customer value:** {r['customer_value']}")
            for k, j in r["ai"].items():
                st.markdown(f"- **{FACTORS[k]['label']}** (AI-judged): {j['score']}/5 — {j['justification']}")
            c = r["computed"]
            st.markdown(f"- **Voice-of-customer volume** (computed): {c['voice_volume_raw']} unique comments on {', '.join(c['topics']) or '–'}")
            st.markdown(f"- **Market volume 2030** (computed): {c['market_volume']:.0%} of the line's EU+CN+US volume")
            st.markdown(f"- **Evidence strength** (computed): {c['evidence_strength']:.2f}")
        with t2:
            render_evidence(r["evidence"])
        with t3:
            st.markdown("**Forward-looking assumptions**")
            for a in r["assumptions"] or ["none stated"]:
                st.markdown(f"- 💭 {a}")
            st.markdown("**Uncertainties**")
            for u in r["uncertainties"] or ["none stated"]:
                st.markdown(f"- ❓ {u}")
            st.markdown("**Conflicting evidence**")
            for x in r["conflicting_evidence"] or ["none stated"]:
                st.markdown(f"- ⚔️ {x}")
        with t4:
            a1, a2 = st.columns(2)
            if a1.button("😈 Challenge this requirement", key=f"ch_{r['id']}"):
                with st.spinner("Stress-testing ..."):
                    try:
                        pipeline.challenge(ws, r)
                        st.rerun()
                    except llm.LLMError as e:
                        st.error(str(e))
            if a2.button("🌐 Research competitors & trends", key=f"rs_{r['id']}"):
                with st.spinner("Searching the web ..."):
                    try:
                        pipeline.research(ws, r, vehicle, ctx["comments"], ctx["study"])
                        st.rerun()
                    except llm.LLMError as e:
                        st.error(str(e))
            for ch in reversed(r["challenges"]):
                st.markdown(f"**Devil's advocate → {ch['recommendation'].upper()}**: {ch['recommendation_rationale']}")
                st.markdown("Counter-arguments:\n" + "\n".join(f"- {x}" for x in ch["counter_arguments"]))
                st.markdown("Missing evidence:\n" + "\n".join(f"- {x}" for x in ch["missing_evidence"]))
                st.markdown(f"Alternative interpretation: {ch['alternative_interpretation']}  \nRisk if wrong: {ch['risk_if_wrong']}")
                st.divider()
            for res in reversed(r["web_research"]):
                st.markdown("**Web research (external, verify before relying on it)**")
                st.write(res["summary"])
                for s in res["sources"]:
                    st.markdown(f"- 🌐 [{s['title']}]({s['url']})")
        with t5:
            for v in r["versions"]:
                st.markdown(f"- {v['ts']}: statement changed — *{v['before']}*")
            st.caption("Full history on the Audit Trail page.")

        st.markdown("**Decision**")
        new_stmt = st.text_area("Requirement statement (edit to modify)", r["statement"], key=f"st_{r['id']}", height=80)
        note = st.text_input("Rationale (required)", value=r.get("pm_note", ""), key=f"nt_{r['id']}")
        d = st.columns([1, 1, 1, 1, 3])
        for col, (btn, status) in zip(d, [("✅ Approve", "approved"), ("✏️ Save as modified", "modified"),
                                           ("⏸️ Postpone", "postponed"), ("🛑 Reject", "rejected")]):
            if col.button(btn, key=f"{status}_{r['id']}"):
                if not note.strip():
                    st.error("Please give a rationale — every decision is logged.")
                elif status == "modified" and new_stmt.strip() == r["statement"].strip():
                    st.error("Edit the statement first, or use Approve.")
                else:
                    before = {"status": r["status"], "statement": r["statement"]}
                    if new_stmt.strip() != r["statement"].strip():
                        r["versions"].append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "before": r["statement"]})
                        r["statement"] = new_stmt.strip()
                    r["status"], r["pm_note"] = status, note
                    save_workspace(ws)
                    log_event(ws["key"], "PM", f"requirement_{status}", "requirement", r["id"], before=before,
                              after={"status": status, "statement": r["statement"], "score": float(row["priority_score"]),
                                     "weights": weights}, rationale=note)
                    st.rerun()
