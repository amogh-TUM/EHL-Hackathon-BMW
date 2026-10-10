"""Pipeline actions shared by several views; each engine run is shown as a visible step."""
from __future__ import annotations

import streamlit as st

from src.core import llm, pipeline
from src.core.store import log_event
from src.ui.common import option_text


def run_analysis(ctx: dict, vehicle: str, markets: list[str]) -> bool:
    ws = ctx["ws"]
    if ws["insights"]:
        log_event(ws["key"], "PM", "regenerate_insights", "insight_set", ws["key"], before=[i["id"] for i in ws["insights"]])
    with st.status("Running the analysis pipeline (takes ~2 min) ...", expanded=True) as status:
        st.write("① Source engine — loaded feedback, customer study, sales; data gaps detected (deterministic)")
        st.write("② Signal engine — AI synthesises customer insights with citations ...")
        try:
            pipeline.run_insights(ws, vehicle, markets, ctx["comments"], ctx["cls"], ctx["study"], ctx["sales"], ctx["gaps"])
        except llm.LLMError as e:
            status.update(label=f"Stopped: {e}", state="error")
            return False
        st.write(f"③ Citation check — {sum(len(i['evidence']) for i in ws['insights'])} citations verified against the dataset")
        status.update(label="Analysis complete — review the insights (Gate 1)", state="complete")
    return True


def run_draft_and_check(ctx: dict, vehicle: str) -> bool:
    ws = ctx["ws"]
    if ws["requirements"]:
        log_event(ws["key"], "PM", "regenerate_requirements", "requirement_set", ws["key"],
                  before=[(r["id"], r["status"]) for r in ws["requirements"]])
    with st.status("Drafting and self-checking requirements (takes ~4-5 min) ...", expanded=True) as status:
        st.write("④ Synthesis engine — AI drafts customer-facing requirements from your accepted insights ...")
        try:
            pipeline.run_requirements(ws, vehicle, ctx["comments"], ctx["cls"], ctx["study"], ctx["sales"], option_text(vehicle))
            st.write(f"   {len(ws['requirements'])} drafts · option list checked · citations verified")
            st.write("⑤ Evaluation engine — AI reviews every draft: BMW brand lens, evidence check, wording ...")
            pipeline.run_evaluation(ws)
        except llm.LLMError as e:
            status.update(label=f"Stopped: {e}", state="error")
            return False
        n_sug = sum((r.get("evaluation") or {}).get("suggestion_changed", False) for r in ws["requirements"])
        st.write(f"   {n_sug} wording improvements suggested (logged to the change log, not applied)")
        st.write("⑥ Priority engine — transparent weighted score computed")
        status.update(label="Drafts ready — decide them in the Decision Studio (Gate 2)", state="complete")
    return True


def run_evaluation_only(ctx: dict) -> bool:
    with st.status("Evaluation engine reviewing the drafts ...", expanded=True) as status:
        try:
            pipeline.run_evaluation(ctx["ws"])
        except llm.LLMError as e:
            status.update(label=f"Stopped: {e}", state="error")
            return False
        status.update(label="Self-check complete", state="complete")
    return True
