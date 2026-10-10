import streamlit as st

from src.core.config import MARKETS, MODEL, PROVIDER, VEHICLES
from src.ui.common import ai_ready, context, get_scope, ranked_requirements, step_states
from src.ui.theme import callout, e, footer, pill, side_title, stat, stepper

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws, comments, sales = ctx["ws"], ctx["comments"], ctx["sales"]
cfg = VEHICLES[vehicle]
s = sales.set_index("market_code")
vol_2030 = int(s.loc[s.index.isin(markets), "volume_2030"].sum())
live = ai_ready()

# ---------- hero with the agent orchestration panel (maps 1:1 to the real pipeline) ----------
n_acc = sum(i["status"] == "accepted" for i in ws["insights"])
n_dec = sum(r["status"] != "proposed" for r in ws["requirements"])
n_eval = sum("evaluation" in r for r in ws["requirements"])
state = (f'<i style="background:#58d2ad;box-shadow:0 0 9px #58d2ad"></i> LIVE · {e(PROVIDER.upper())}' if live
         else '<i style="background:#c8912f"></i> OFFLINE · NO API KEY')
st.html(f"""
<section class="bmw-hero">
  <div>
    <div class="bmw-kicker">/// Customer evidence → product decisions</div>
    <h1>Customer voice.<br><span>Product clarity.</span></h1>
    <p>A product-management workspace that turns real-world feedback, customer studies and sales data into traceable,
       prioritised customer requirements for the next {e(cfg['name'].split(' (')[0])} generation. Inspect the signal,
       challenge the interpretation, and make the decision with its evidence in view.</p>
  </div>
  <div class="agent">
    <div class="agent-top"><span class="agent-orbit">AI</span>
      <div><b>Agentic AI</b><small>ORCHESTRATION · {e(MODEL)}</small></div>
      <span class="agent-state">{state}</span></div>
    <div class="agent-grid">
      <div class="agent-node"><span>01</span><b>Signal engine</b><small>{len(ws['insights'])} insights · citations verified</small></div>
      <div class="agent-node"><span>02</span><b>Synthesis engine</b><small>{len(ws['requirements'])} requirement drafts</small></div>
      <div class="agent-node"><span>03</span><b>Evaluation engine</b><small>{n_eval} self-reviewed · brand lens</small></div>
      <div class="agent-node"><span>04</span><b>Priority engine</b><small>Transparent weighted score</small></div>
    </div>
    <div class="agent-gate"><span>HUMAN DECISION GATES</span><b>{n_acc} insights accepted · {n_dec} decisions</b></div>
    <div class="agent-scope"><b>{e(cfg['name'].upper())}</b>
      <div class="meta-line">{e(' · '.join(MARKETS[m].upper() for m in markets))}</div>
      <div class="meta-line">2030 VOLUME IN SCOPE · {vol_2030:,}</div></div>
  </div>
  <div class="photo-credit">BMW GROUP PRESS IMAGE · i7 M70 xDRIVE</div>
</section>""")

# ---------- guided flow ----------
states = step_states(ws)
stepper(states)
NEXT = {0: ("▶ Step 1 · Run the analysis", "views/insight_explorer.py"),
        1: ("▶ Step 2 · Pick the insights that matter", "views/insight_explorer.py"),
        2: ("▶ Step 3 · Draft & self-check requirements", "views/board.py"),
        3: ("▶ Step 4 · Decide in the Decision Studio", "views/studio.py")}
step_now = states.index("now") if "now" in states else None
cta1, cta2 = st.columns([3, 1.3])
if step_now is None:
    cta1.success("All requirements decided — export the result from Trace.")
    if cta2.button("Open Trace →", width="stretch"):
        st.switch_page("views/trace.py")
else:
    label, target = NEXT[step_now]
    cta1.markdown(f"**Next:** {label.split('· ', 1)[1]}")
    if cta2.button(label, type="primary", width="stretch"):
        st.switch_page(target)

# ---------- metrics ----------
in_scope = comments[comments["market"].isin(markets)]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Distinct feedback records", f"{len(in_scope):,}", f"of {len(comments):,} total", delta_color="off")
m2.metric("Insights accepted", f"{n_acc} / {len(ws['insights'])}")
m3.metric("Requirements decided", f"{n_dec} / {len(ws['requirements'])}")
m4.metric("2030 volume in scope", f"{vol_2030:,}")

# ---------- priority recommendations + data in scope ----------
left, right = st.columns([1.55, 0.75], gap="medium")
with left:
    with st.container(border=True):
        scored, sens = ranked_requirements(ws)
        h1, h2 = st.columns([3, 1])
        h1.markdown("### Priority recommendations")
        if h2.button("Open Decision Studio →", type="tertiary"):
            st.switch_page("views/studio.py")
        if scored is not None:
            by_id = {r["id"]: r for r in ws["requirements"]}
            rows = []
            for i, row in enumerate(scored.itertuples()):
                r = by_id[row.id]
                pills = pill(f"{r['computed']['voice_volume_raw']} tagged records") + pill(f"confidence {r['confidence']}",
                        "warn" if r["confidence"] == "low" else "") + pill(r["status"], r["status"])
                if not bool(sens.loc[row.id, "robust"]):
                    pills += pill("rank sensitive to weights", "warn")
                rows.append(f'<div class="req-row"><div class="req-index">{i + 1:02d}</div><div><div class="req-title">{e(r["title"])}</div>'
                            f'<div class="req-sub">{e(r["statement"])}</div><div>{pills}</div></div>'
                            f'<div class="freq"><b>{row.priority_score:.0f}</b><small>PRIORITY</small></div></div>')
            st.html("".join(rows))
        elif ws["insights"]:
            rows = []
            for i, ins in enumerate(ws["insights"]):
                rows.append(f'<div class="req-row"><div class="req-index">{i + 1:02d}</div><div><div class="req-title">{e(ins["title"])}</div>'
                            f'<div class="req-sub">{e(ins["insight_type"].replace("_", " "))} · {e(", ".join(ins["vfc_topics"][:3]))}</div>'
                            f'<div>{pill(ins["status"], ins["status"])}{pill(ins["evidence_basis"].replace("_", " "))}</div></div>'
                            f'<div class="freq"><b>{len(ins["evidence"])}</b><small>EVIDENCE</small></div></div>')
            st.html(callout("Next step", "Review the insights (Gate 1), then generate requirements to get a ranked backlog.") + "".join(rows))
        else:
            st.html(callout("Start here", "Generate insights on the Insights page. The AI proposes, you decide at two gates."))

with right:
    with st.container(border=True):
        counts = "".join(stat(f"{MARKETS[m]} verbatims", f"{int((comments['market'] == m).sum()):,}") for m in markets)
        st.html(side_title("Data in scope", "INGESTED SOURCES")
                + stat("Distinct feedback IDs", f"{len(comments):,}")
                + counts
                + stat("2025 volume (scope)", f"{int(s.loc[s.index.isin(markets), 'volume_2025'].sum()):,}")
                + stat("2030 volume (scope)", f"{vol_2030:,}")
                + callout("Read the counts correctly", "Category totals count distinct IDs per tag and overlap. Feedback shows what to investigate, not prevalence.")
                + "".join(callout("Data gap", g, warn=True) for g in ctx["gaps"]))
    with st.container(border=True):
        st.html(side_title("Product context", "BMW OPTION LIST")
                + stat(f"{cfg['name'].split(' (')[0]} option list", "Germany · 2026")
                + callout("Market boundary", "The option list documents Germany-market equipment and packages. It is configuration context, "
                          "not proof of availability in other markets or of an unmet customer need.", warn=True))

with st.expander("How it works · a sequential AI pipeline with two human gates"):
    st.markdown("""
| # | Engine | Who | Output |
|---|---|---|---|
| 0 | **Source engine** — load feedback, customer study, sales, option list; detect data gaps | System (deterministic) | topic stats, gaps |
| 1 | **Signal engine** — customer needs & pain points with citations, machine-verified | AI | insights (JSON) |
| ★ | **Gate 1** — keep the insights that matter | **Product manager** | accepted insights |
| 2 | **Synthesis engine** — customer-facing requirements with evidence, assumptions, conflicts | AI | requirement drafts |
| 3 | **Evaluation engine** — critiques every draft: BMW brand lens, evidence check, wording; suggestions go to the change log | AI | reviews, suggestions |
| 4 | **Priority engine** — weighted score, AI-judged vs computed factors, robustness across presets | System, PM-owned weights | ranking |
| ★ | **Gate 2** — approve / modify / postpone / reject with reasons | **Product manager** | decisions |
| ∞ | **Trace** — append-only audit log, change log, trace to raw verbatims, exports | System | audit trail |

Each engine has one focused job and a strict JSON schema; they run in a fixed order (no autonomous agent loops). **AI never approves anything.**
""")
footer()
