"""Entry point: streamlit run app.py  - router with BMW top navigation; views live in views/."""
import streamlit as st

st.set_page_config(page_title="TRACE · Requirement Intelligence", page_icon="assets/trace_icon.svg", layout="wide")

from src.ui.common import scope_sidebar  # noqa: E402
from src.ui.theme import inject  # noqa: E402

inject()
st.logo("assets/trace_logo.svg", icon_image="assets/trace_icon.svg", size="large")
scope_sidebar()

nav = st.navigation([
    st.Page("views/overview.py", title="Overview", default=True),
    st.Page("views/insight_explorer.py", title="Insight Explorer"),
    st.Page("views/board.py", title="Requirement Board"),
    st.Page("views/studio.py", title="Decision Studio"),
    st.Page("views/audit.py", title="Audit Trail"),
], position="top")
nav.run()
