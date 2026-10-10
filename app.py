"""Entry point: streamlit run app.py  - router with BMW top navigation; views live in views/."""
import streamlit as st

st.set_page_config(page_title="BMW Product Intelligence", page_icon="🚗", layout="wide")

from src.ui.common import scope_sidebar  # noqa: E402
from src.ui.theme import inject  # noqa: E402

inject()
scope_sidebar()

nav = st.navigation([
    st.Page("views/overview.py", title="Overview", default=True),
    st.Page("views/evidence.py", title="Evidence"),
    st.Page("views/insights.py", title="Insights"),
    st.Page("views/requirements.py", title="Requirements"),
    st.Page("views/decisions.py", title="PM decisions"),
    st.Page("views/sources.py", title="Sources"),
    st.Page("views/audit.py", title="Audit trail"),
], position="top")
nav.run()
