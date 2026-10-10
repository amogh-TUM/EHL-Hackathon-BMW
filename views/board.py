import plotly.express as px
import streamlit as st

from src.core.scoring import DEFAULT_WEIGHTS, FACTORS, PRESETS, factor_table, score, sensitivity
from src.core.store import STATUSES, log_event, save_workspace
from src.ui.actions import run_draft_and_check, run_evaluation_only
from src.ui.common import ai_ready, context, gaps_box, get_scope, step_states
from src.ui.theme import callout, e, page_head, stepper

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws = ctx["ws"]
reqs = ws["requirements"]

page_head("Steps 3-4 · Synthesis, evaluation & priority engines", "Requirement Board",
          "Every AI-drafted requirement, ranked by a transparent score. Open a card in the Decision Studio to decide it.")
stepper(step_states(ws))
gaps_box(ctx["gaps"])

n_acc = sum(i["status"] == "accepted" for i in ws["insights"])
if not reqs:
    st.info(f"No requirements yet. {n_acc} accepted insight(s) available." +
            ("" if n_acc else " Accept insights in the Insight Explorer first (Gate 1)."))
    if st.button("▶ Draft & self-check requirements", type="primary", disabled=n_acc == 0 or not ai_ready()):
        if run_draft_and_check(ctx, vehicle):
            st.rerun()
    st.stop()

top1, top2, top3 = st.columns([3, 1.2, 1.2])
if any("evaluation" not in r for r in reqs):
    top1.warning("Some drafts have not been through the evaluation engine yet.")
    if top2.button("Run self-check", type="primary", disabled=not ai_ready(), width="stretch"):
        if run_evaluation_only(ctx):
            st.rerun()
if top3.button("↻ Re-draft from insights", disabled=n_acc == 0 or not ai_ready(), width="stretch",
               help="Replaces all drafts (the old set stays in the audit log)"):
    if run_draft_and_check(ctx, vehicle):
        st.rerun()

# ---------- weights (PM-owned) ----------
weights = ws.get("weights") or DEFAULT_WEIGHTS
with st.expander("⚖️ How priority is calculated — adjust the weights", expanded=False):
    preset = st.segmented_control("Preset", list(PRESETS), default=None, key="preset")
    base = PRESETS[preset] if preset else {f: weights.get(f, DEFAULT_WEIGHTS[f]) for f in FACTORS}
    cols = st.columns(4)
    new_w = {f: cols[i % 4].slider(f"{m['label']} · {m['origin']}", 0, 50, int(base[f]), help=m["help"], key=f"w_{preset}_{f}")
             for i, (f, m) in enumerate(FACTORS.items())}
    if st.button("Save weights"):
        log_event(ws["key"], "PM", "set_weights", "weights", ws["key"], before=ws.get("weights"), after=new_w)
        ws["weights"] = new_w
        save_workspace(ws)
        st.rerun()
    weights = new_w
    st.caption("Score = Σ (weight × factor) / Σ weights × 100. AI-judged factors carry written justifications; computed factors come from the data.")

ft = factor_table(reqs)
scored = score(ft, weights).set_index("id")
sens = sensitivity(ft)

# ---------- kanban ----------
COLUMNS = [("proposed", "To decide"), ("approved", "Approved"), ("postponed", "Postponed"), ("rejected", "Rejected")]
VERDICT = {"ready_for_decision": "✓ ready", "revise_first": "✎ revise first", "needs_more_evidence": "🕳 needs evidence"}
cols = st.columns(4, gap="small")
for col, (status, label) in zip(cols, COLUMNS):
    items = [r for r in reqs if (r["status"] in ("approved", "modified") if status == "approved" else r["status"] == status)]
    items.sort(key=lambda r: scored.loc[r["id"], "rank"])
    with col:
        st.html(f'<div class="kanban-head"><span>{label}</span><span>{len(items)}</span></div>')
        for r in items:
            ev = r.get("evaluation") or {}
            flags = []
            if ev:
                flags.append(VERDICT.get(ev.get("verdict"), ""))
            if r["confidence"] == "low":
                flags.append("low confidence")
            if not bool(sens.loc[r["id"], "robust"]):
                flags.append("rank sensitive")
            if r["status"] == "modified":
                flags.append("modified")
            with st.container(border=True):
                st.html(f'<div class="kcard" style="border:0;padding:0;margin:0"><span class="s">{scored.loc[r["id"], "priority_score"]:.0f}</span>'
                        f'<div class="t">#{int(scored.loc[r["id"], "rank"])} {e(r["title"])}</div>'
                        f'<div class="m">{e(" · ".join(r["target_markets"]))} · {e(" · ".join(f for f in flags if f))}</div></div>')
                if st.button("Open in studio →", key=f"open_{r['id']}", type="tertiary"):
                    st.session_state["studio_focus"] = r["id"]
                    st.switch_page("views/studio.py")

if ws.get("portfolio_notes"):
    st.html(callout("Evaluation engine · portfolio notes", " · ".join(ws["portfolio_notes"])))

# ---------- ranking detail ----------
with st.expander("📊 Ranking breakdown & robustness"):
    s2 = scored.reset_index()
    contrib = s2.melt(id_vars=["id", "title", "priority_score"], value_vars=[f"contrib_{f}" for f in FACTORS],
                      var_name="factor", value_name="points")
    contrib["factor"] = contrib["factor"].str.replace("contrib_", "").map(lambda f: f"{FACTORS[f]['label']} ({FACTORS[f]['origin']})")
    contrib["label"] = contrib["id"] + " · " + contrib["title"].str.slice(0, 45)
    fig = px.bar(contrib, y="label", x="points", color="factor", orientation="h",
                 category_orders={"label": (s2["id"] + " · " + s2["title"].str.slice(0, 45)).tolist()},
                 height=140 + 36 * len(s2))
    fig.update_layout(yaxis_title=None, xaxis_title="priority score (0-100)", legend_title=None,
                      margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")
    table = s2[["rank", "id", "title", "priority_score"]].merge(sens[["best_rank", "worst_rank", "robust"]], left_on="id", right_index=True)
    table["status"] = table["id"].map({r["id"]: r["status"] for r in reqs})
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"robust": st.column_config.CheckboxColumn("robust", help="Rank varies ≤2 places across all presets")})
    st.caption(f"Statuses: {', '.join(STATUSES)}. Best/worst rank = range across weighting presets; non-robust items depend on how you weigh trade-offs.")
