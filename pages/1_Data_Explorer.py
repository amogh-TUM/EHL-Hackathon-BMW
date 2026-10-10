import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Data Explorer", page_icon="📊", layout="wide")

from src.core.config import MARKETS  # noqa: E402
from src.core.evidence import topic_stats  # noqa: E402
from src.ui.common import context, gaps_box, scope_sidebar  # noqa: E402

vehicle, markets = scope_sidebar()
ctx = context(vehicle, markets)
comments, cls, study, sales = ctx["comments"], ctx["cls"], ctx["study"], ctx["sales"]

st.title("📊 Data Explorer")
st.caption("Deterministic view of the provided data — no AI involved on this page.")
gaps_box(ctx["gaps"])

tab_fb, tab_study, tab_sales, tab_search = st.tabs(["Feedback topics", "Customer study", "Sales", "Verbatim search"])

with tab_fb:
    stats = topic_stats(comments, cls, markets)
    if stats.empty:
        st.warning("No classified feedback for the selected markets.")
    else:
        top = stats.head(25)
        long = top.melt(id_vars="topic", value_vars=["likes", "wants", "difficult", "defects"], var_name="type", value_name="comments")
        fig = px.bar(long, y="topic", x="comments", color="type", orientation="h", height=700,
                     color_discrete_map={"likes": "#2e7d32", "wants": "#1565c0", "difficult": "#ef6c00", "defects": "#c62828"},
                     category_orders={"topic": top["topic"].tolist()})
        fig.update_layout(yaxis_title=None, legend_title=None, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(stats, width="stretch", hide_index=True)
    st.caption("One comment can carry several classifications; counts are unique comments per topic. Unclassified comments ('no_class_found') are excluded from topic counts but searchable.")

with tab_study:
    s = study[study["market"].isin(markets)]
    if s.empty:
        st.warning("No customer-study data for this vehicle in the selected markets.")
    else:
        st.caption("Scores normalised to 0-100 (CN/EU: mean of 1-10 scale; US: mean of 7-point scale). Different questionnaires per region — compare within a market, not across.")
        for m in markets:
            part = s[s["market"] == m].sort_values("score")
            if part.empty:
                st.info(f"No study data for {MARKETS[m]}.")
                continue
            st.markdown(f"**{MARKETS[m]}** — lowest-rated attributes first")
            fig = px.bar(part.head(15), x="score", y="attribute", orientation="h", hover_data=["metric"], height=420)
            fig.update_layout(yaxis_title=None, yaxis_autorange="reversed", margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width="stretch")

with tab_sales:
    st.dataframe(sales, width="stretch", hide_index=True)
    long = sales.melt(id_vars="market", value_vars=["volume_2024", "volume_2025", "volume_2030"], var_name="year", value_name="units")
    st.plotly_chart(px.bar(long, x="market", y="units", color="year", barmode="group"), width="stretch")

with tab_search:
    q = st.text_input("Search verbatims (e.g. 'carplay', 'range', 'idrive')")
    view = comments[comments["market"].isin(markets)]
    if q:
        view = view[view["text"].astype(str).str.contains(q, case=False, na=False)]
    st.caption(f"{len(view):,} comments")
    st.dataframe(view.head(500), width="stretch", hide_index=True)
