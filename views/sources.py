import streamlit as st

from src.core.config import SALES_FILE, STUDY_FILE, VEHICLES
from src.ui.common import context, get_scope
from src.ui.theme import e, page_head

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
ws, comments, cls, study = ctx["ws"], ctx["comments"], ctx["cls"], ctx["study"]
cfg = VEHICLES[vehicle]

page_head("Source register", "Ingested and contextual sources",
          "Every source the copilot uses, what it is good for, and where its boundaries are.")

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
