"""Entry point: streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="BMW Requirement Copilot", page_icon="🚗", layout="wide")

from src.core.config import MARKETS, VEHICLES  # noqa: E402
from src.ui.common import context, gaps_box, scope_sidebar  # noqa: E402

vehicle, markets = scope_sidebar()
ctx = context(vehicle, markets)
ws = ctx["ws"]

st.title("🚗 BMW Requirement Copilot")
st.caption("AI-assisted derivation, justification and prioritisation of customer requirements for the next vehicle generation — the product manager decides.")

c1, c2, c3, c4 = st.columns(4)
in_scope = ctx["comments"][ctx["comments"]["market"].isin(markets)]
c1.metric("Feedback comments (in scope)", f"{len(in_scope):,}", f"of {len(ctx['comments']):,} total")
c2.metric("Insights (accepted / total)", f"{sum(i['status'] == 'accepted' for i in ws['insights'])} / {len(ws['insights'])}")
c3.metric("Requirements decided", f"{sum(r['status'] != 'proposed' for r in ws['requirements'])} / {len(ws['requirements'])}")
s = ctx["sales"].set_index("market_code")
c4.metric("2030 volume in scope", f"{int(s.loc[s.index.isin(markets), 'volume_2030'].sum()):,} units")

gaps_box(ctx["gaps"])

st.subheader("Workflow, roles and decision gates")
st.markdown("""
| Step | What happens | Who | Gate |
|---|---|---|---|
| 1. Data | Load feedback, customer study, sales, option list; compute topic statistics and data gaps | **System** (deterministic) | – |
| 2. Insights | Synthesise customer needs / pain points with cited evidence; citations are machine-verified against the data | **AI proposes** | **Gate 1 – PM accepts / rejects / annotates each insight** |
| 3. Requirements | Turn accepted insights into customer-facing requirements with evidence, assumptions, uncertainties, conflicts | **AI proposes** | – |
| 4. Prioritisation | Transparent weighted score; AI-judged and computed factors are labelled; sensitivity across weighting presets | **System computes, PM sets weights** | – |
| 5. Review | Challenge (AI devil's advocate), web research, edit; approve / modify / postpone / reject with mandatory rationale | **PM decides** | **Gate 2 – every requirement needs a PM decision** |
| 6. Trace | Every AI output and PM decision is appended to an immutable audit log; full trace to raw verbatims | **System** | – |

**AI never approves anything.** Nothing leaves the *proposed* state without a logged human decision.
""")

st.subheader("Data sources")
st.markdown(f"""
- **Customer feedback** — {VEHICLES[vehicle]['feedback']} (pre-classified by VFC topic and feedback type)
- **Customer study 2025** — CN/EU satisfaction (1-10) and US rating distributions (7-point), normalised to 0-100
- **Sales volumes** — 2024, 2025 and 2030 forecast by market
- **Option list** — current German price/equipment list (what is already offered)
- **Web research** (on demand) — competitor offers and trends, cited with URLs and labelled *external*
""")
st.info("Use the pages in the sidebar: **Data Explorer → Insights → Requirements → Audit Trail**.")
