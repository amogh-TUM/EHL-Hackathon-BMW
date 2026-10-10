"""Orchestrates the AI stages. Every AI output enters the workspace as 'proposed' and is logged."""
from __future__ import annotations

import json

import pandas as pd

from . import llm, prompts
from .config import VEHICLES
from .evidence import build_insight_context, evidence_strength, sample_quotes, topic_stats, verify_evidence
from .schemas import Challenge, InsightSet, RequirementSet
from .scoring import market_volume, voice_volume_raw
from .store import log_event, save_workspace


def run_insights(ws: dict, vehicle: str, markets: list[str], comments: pd.DataFrame, cls: pd.DataFrame,
                 study: pd.DataFrame, sales: pd.DataFrame, gaps: list[str], n_topics: int = 30) -> dict:
    stats = topic_stats(comments, cls, markets)
    topics = stats["topic"].head(n_topics).tolist()
    quotes = sample_quotes(comments, cls, markets, topics)
    context = build_insight_context(VEHICLES[vehicle]["name"], markets, stats, quotes, study, sales, gaps)

    result, meta = llm.structured(prompts.INSIGHT_SYSTEM, context, InsightSet)
    insights = []
    for ins in result.insights:
        d = ins.model_dump()
        d["evidence"] = verify_evidence(d["evidence"], comments, study)
        d["status"] = "proposed"
        d["pm_note"] = ""
        insights.append(d)
    ws["insights"] = insights
    ws["insight_caveats"] = result.overall_caveats
    ws["runs"].append({"stage": "insights", "prompt_version": prompts.PROMPT_VERSION, **meta})
    save_workspace(ws)
    log_event(ws["key"], "AI", "generate_insights", "insight_set", ws["key"],
              after=[i["id"] for i in insights], meta={**meta, "prompt_version": prompts.PROMPT_VERSION,
                                                        "n_quotes": len(quotes), "n_topics": len(topics)})
    return ws


def run_requirements(ws: dict, vehicle: str, comments: pd.DataFrame, cls: pd.DataFrame,
                     study: pd.DataFrame, sales: pd.DataFrame, option_text: str) -> dict:
    accepted = [i for i in ws["insights"] if i["status"] == "accepted"]
    if not accepted:
        raise llm.LLMError("No accepted insights - review and accept insights first (decision gate 1).")
    payload = (
        f"# Vehicle: {VEHICLES[vehicle]['name']}\n\n"
        "## PM-approved insights (with verified evidence and PM notes)\n"
        + json.dumps(accepted, indent=1, ensure_ascii=False)
        + "\n\n## Sales volumes\n" + sales.to_csv(index=False)
        + "\n\n## Current option list (German price list, for checking what is already offered)\n" + option_text
    )
    result, meta = llm.structured(prompts.REQUIREMENT_SYSTEM, payload, RequirementSet)

    topics_by_insight = {i["id"]: i.get("vfc_topics", []) for i in accepted}
    reqs = []
    for r in result.requirements:
        d = r.model_dump()
        d["evidence"] = verify_evidence(d["evidence"], comments, study)
        topics = sorted({t for iid in d["linked_insight_ids"] for t in topics_by_insight.get(iid, [])})
        d["ai"] = {k: d.pop(k) for k in ("customer_impact", "future_relevance", "competitive_gap")}
        for k in d["ai"]:
            d["ai"][k]["score"] = max(1, min(5, int(d["ai"][k]["score"])))
        d["computed"] = {
            "voice_volume_raw": voice_volume_raw(topics, d["target_markets"], cls),
            "market_volume": market_volume(d["target_markets"], sales),
            "evidence_strength": evidence_strength(d["evidence"]),
            "topics": topics,
        }
        d.update(status="proposed", pm_note="", versions=[], challenges=[], web_research=[])
        reqs.append(d)
    ws["requirements"] = reqs
    ws["runs"].append({"stage": "requirements", "prompt_version": prompts.PROMPT_VERSION, **meta})
    save_workspace(ws)
    log_event(ws["key"], "AI", "generate_requirements", "requirement_set", ws["key"],
              after=[r["id"] for r in reqs],
              meta={**meta, "prompt_version": prompts.PROMPT_VERSION, "from_insights": [i["id"] for i in accepted]})
    return ws


def challenge(ws: dict, req: dict) -> dict:
    view = {k: req[k] for k in ("statement", "customer_value", "target_markets", "evidence", "assumptions",
                                 "uncertainties", "conflicting_evidence", "ai", "computed", "confidence")}
    result, meta = llm.structured(prompts.CHALLENGE_SYSTEM, json.dumps(view, ensure_ascii=False, indent=1),
                                  Challenge, effort="medium", max_tokens=16000)
    ch = result.model_dump()
    req["challenges"].append(ch)
    save_workspace(ws)
    log_event(ws["key"], "AI", "challenge", "requirement", req["id"], after=ch, meta=meta)
    return ch


def research(ws: dict, req: dict, vehicle: str, comments: pd.DataFrame, study: pd.DataFrame) -> dict:
    q = (f"For the successor of the {VEHICLES[vehicle]['name']} (markets: {', '.join(req['target_markets'])}), "
         f"find current competitor offers, reviews and 3-5 year trends relevant to this customer need: "
         f"\"{req['statement']}\". What do competitors (e.g. Mercedes-Benz, Audi, Tesla, NIO, Li Auto, BYD, Lexus) offer, "
         f"and is the need growing?")
    res = llm.web_research(q)
    new_ev = [{"source_type": "web", "ref": s["url"], "detail": (s["cited_text"] or s["title"])[:300],
               "market": "ALL", "supports": True} for s in res["sources"]]
    req["web_research"].append(res)
    req["evidence"] = verify_evidence(req["evidence"] + new_ev, comments, study)
    req["computed"]["evidence_strength"] = evidence_strength(req["evidence"])
    save_workspace(ws)
    log_event(ws["key"], "AI", "web_research", "requirement", req["id"],
              after={"summary": res["summary"], "sources": [s["url"] for s in res["sources"]]}, meta={"model": res["model"]})
    return res
