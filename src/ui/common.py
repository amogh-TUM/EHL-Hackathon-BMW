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


def scope_sidebar() -> tuple[str, list[str]]:
    ss = st.session_state
    ss.setdefault("vehicle", "G60")
    ss.setdefault("markets", ["EU", "US"])
    # Re-assigning keeps widget state alive when switching between pages.
    ss.vehicle, ss.markets = ss.vehicle, ss.markets
    with st.sidebar:
        st.subheader("Scope")
        vehicle = st.selectbox("Vehicle line", list(VEHICLES), format_func=lambda v: VEHICLES[v]["name"], key="vehicle")
        markets = st.multiselect("Markets", list(MARKETS), format_func=lambda m: f"{MARKETS[m]} ({m})", key="markets")
        if not markets:
            st.warning("Select at least one market.")
            st.stop()
        st.caption(f"AI: `{PROVIDER}` · `{MODEL}`")
        key = os.getenv(API_KEY_VAR, "").strip()
        if not key or key.endswith("..."):
            st.error(f"{API_KEY_VAR} not set - add it to `.env`. Data views still work.")
    return vehicle, markets


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
