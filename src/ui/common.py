"""Shared Streamlit helpers: cached data access, scope selector, small render helpers."""
from __future__ import annotations

import os

import streamlit as st

from src.core import data_loader as dl
from src.core.config import API_KEY_VAR, MARKETS, MODEL, PROVIDER, VEHICLES
from src.core.evidence import coverage_report
from src.core.store import load_workspace, workspace_key


@st.cache_data(show_spinner="Loading feedback ...")
def feedback(vehicle: str):
    return dl.load_feedback(vehicle)


@st.cache_data
def sales_all():
    return dl.load_sales()


@st.cache_data
def study(vehicle: str):
    return dl.study_for_vehicle(vehicle)


@st.cache_data
def option_text(vehicle: str):
    return dl.load_option_list_text(vehicle)


def ai_ready() -> bool:
    key = os.getenv(API_KEY_VAR, "").strip()
    return bool(key) and not key.endswith("...")


def scope_sidebar() -> tuple[str, list[str]]:
    """Rendered once by the router (app.py); views read the scope via get_scope()."""
    ss = st.session_state
    ss.setdefault("vehicle", "G60")
    ss.setdefault("markets", ["CN", "EU", "US"])
    # Re-assigning keeps widget state alive when switching between pages.
    ss.vehicle, ss.markets = ss.vehicle, ss.markets
    with st.sidebar:
        st.markdown("#### Scope")
        vehicle = st.selectbox("Vehicle line", list(VEHICLES), format_func=lambda v: VEHICLES[v]["name"], key="vehicle")
        markets = st.multiselect("Markets", list(MARKETS), format_func=lambda m: f"{MARKETS[m]} ({m})", key="markets")
        if not markets:
            st.warning("Select at least one market.")
            st.stop()
        st.caption(f"AI: `{PROVIDER}` · `{MODEL}`")
        if not ai_ready():
            st.error(f"{API_KEY_VAR} not set - add it to `.env`. Data views still work.")
    return vehicle, markets


def get_scope() -> tuple[str, list[str]]:
    return st.session_state["vehicle"], st.session_state["markets"]


def ranked_requirements(ws: dict):
    """Requirements scored with the PM's saved weights (or defaults). Returns (scored_df, sensitivity_df) or (None, None)."""
    from src.core.scoring import DEFAULT_WEIGHTS, factor_table, score, sensitivity
    if not ws["requirements"]:
        return None, None
    ft = factor_table(ws["requirements"])
    return score(ft, ws.get("weights") or DEFAULT_WEIGHTS), sensitivity(ft)


def context(vehicle: str, markets: list[str]) -> dict:
    comments, cls = feedback(vehicle)
    sales = sales_all()[vehicle]
    stdy = study(vehicle)
    key = workspace_key(vehicle, markets)
    return {"comments": comments, "cls": cls, "sales": sales, "study": stdy,
            "gaps": coverage_report(comments, markets, stdy, sales), "key": key, "ws": load_workspace(key)}


VERIF_ICON = {"verified": "✅", "partially": "🟡", "unverified": "❌", "external": "🌐", "assumption": "💭"}


def verif_icon(v: str) -> str:
    for k, icon in VERIF_ICON.items():
        if str(v).startswith(k):
            return icon
    return "•"


def render_evidence(evidence: list[dict]) -> None:
    for e in evidence:
        stance = "supports" if e.get("supports", True) else "**contradicts**"
        st.markdown(f"{verif_icon(e.get('verification', ''))} `{e['source_type']}` **{e['ref']}** ({e.get('market', '')}, {stance}) "
                    f"— {e.get('detail', '')}  \n<small>{e.get('verification', '')}</small>", unsafe_allow_html=True)


def gaps_box(gaps: list[str]) -> None:
    if gaps:
        with st.expander(f"⚠️ {len(gaps)} known data gaps for this scope", expanded=False):
            for g in gaps:
                st.markdown(f"- {g}")
