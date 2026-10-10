import plotly.express as px
import streamlit as st

from src.core.config import MARKETS, VEHICLES
from src.core.evidence import sample_quotes, topic_stats
from src.ui.common import context, gaps_box, get_scope
from src.ui.theme import callout, e, page_head

vehicle, markets = get_scope()
ctx = context(vehicle, markets)
comments, cls, study, sales = ctx["comments"], ctx["cls"], ctx["study"], ctx["sales"]

page_head("Evidence room", "Signals from customer feedback",
          f"{VEHICLES[vehicle]['name']} · category-coded records with source IDs · deterministic view, no AI on this page")
gaps_box(ctx["gaps"])

tab_sig, tab_fb, tab_study, tab_sales, tab_search = st.tabs(
    ["Signal room", "Feedback topics", "Customer study", "Sales", "Verbatim search"])

with tab_sig:
    c1, c2, c3 = st.columns([2, 1, 1])
    typ = c1.selectbox("Signal type", ["All signal types", "Wants", "Difficult to Use", "Defect", "Likes"])
    n_show = c2.slider("Clusters", 5, 40, 15)
    per = c3.slider("Verbatims per cluster", 1, 5, 2)
    stats = topic_stats(comments, cls, markets)
    col = {"Wants": "wants", "Difficult to Use": "difficult", "Defect": "defects", "Likes": "likes"}.get(typ)
    if col:
        stats = stats[stats[col] > 0].sort_values(col, ascending=False)
    stats = stats.head(n_show)
    sub = cls if typ == "All signal types" else cls[cls["feedback_type"] == typ]
    quotes = sample_quotes(comments, sub, markets, stats["topic"].tolist(), per_topic=per, max_len=320)
    rows = []
    for r in stats.itertuples():
        mix = " · ".join(f"{k}: {getattr(r, c)}" for k, c in
                         [("Likes", "likes"), ("Wants", "wants"), ("Difficult", "difficult"), ("Defect", "defects")] if getattr(r, c))
        q = quotes[quotes["topic"] == r.topic]
        qhtml = "<br><br>".join(f'{e(x.text)} <span class="evidence-id">{e(x.id)}</span> <small>({e(x.market)}, {e(x.feedback_type)})</small>'
                                for x in q.itertuples()) or "–"
        markets_split = " · ".join(f"{m}: {int(getattr(r, f'n_{m}', 0))}" for m in markets)
        rows.append(f"<tr><td><b>{e(r.topic)}</b><div style='color:#71808e;font-size:.62rem;margin-top:4px'>{e(markets_split)}</div></td>"
                    f"<td><b>{r.mentions}</b></td><td>{e(mix)}</td><td>{qhtml}</td>"
                    f"<td><span class='evidence-id'>{e(VEHICLES[vehicle]['feedback'])}</span></td></tr>")
    st.html('<table class="bmw-table"><thead><tr><th>Signal cluster</th><th>Tagged records</th><th>Signal mix</th>'
            '<th>Representative verbatims</th><th>Trace</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")
    st.html(callout("Read the counts correctly",
                    "Tagged records count distinct feedback IDs per category. One case can carry several tags, so category totals overlap. "
                    "Feedback is qualitative: it shows what to investigate, not population prevalence.")
            + callout("Market coverage", " · ".join(f"{MARKETS[m]}: {int((comments['market'] == m).sum()):,} verbatims" for m in markets)
                      + ". Markets with few or no verbatims rely on the customer study and external sources.", warn=True))

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
