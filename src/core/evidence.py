"""Deterministic evidence aggregation, context building for the LLM, and citation verification."""
from __future__ import annotations

import re

import pandas as pd

from .config import MARKETS


def topic_stats(comments: pd.DataFrame, cls: pd.DataFrame, markets: list[str]) -> pd.DataFrame:
    """Per VFC topic: unique comments, type split, negativity share, market split."""
    c = cls[cls["market"].isin(markets)] if markets else cls
    if c.empty:
        return pd.DataFrame(columns=["topic", "mentions", "likes", "wants", "defects", "difficult", "negative_share"])
    g = c.groupby("topic")
    stats = pd.DataFrame({
        "mentions": g["id"].nunique(),
        "likes": c[c["feedback_type"] == "Likes"].groupby("topic")["id"].nunique(),
        "wants": c[c["feedback_type"] == "Wants"].groupby("topic")["id"].nunique(),
        "defects": c[c["feedback_type"] == "Defect"].groupby("topic")["id"].nunique(),
        "difficult": c[c["feedback_type"] == "Difficult to Use"].groupby("topic")["id"].nunique(),
    }).fillna(0).astype(int)
    stats["negative_share"] = ((stats["defects"] + stats["difficult"]) / stats["mentions"]).round(2)
    for m in markets:
        stats[f"n_{m}"] = c[c["market"] == m].groupby("topic")["id"].nunique()
    return stats.fillna(0).sort_values("mentions", ascending=False).reset_index()


def coverage_report(comments: pd.DataFrame, markets: list[str], study: pd.DataFrame, sales: pd.DataFrame) -> list[str]:
    """Honest list of data gaps for the selected scope - surfaced to PM and fed to the LLM."""
    gaps = []
    for m in markets:
        n = int((comments["market"] == m).sum())
        if n == 0:
            gaps.append(f"No customer feedback verbatims for {MARKETS[m]} - conclusions for {m} rely on the customer study, sales data and external sources only.")
        elif n < 100:
            gaps.append(f"Only {n} feedback verbatims for {MARKETS[m]} - treat feedback-based conclusions for {m} as weak.")
        if study.empty or m not in set(study["market"]):
            gaps.append(f"No customer-study data for {MARKETS[m]}.")
        row = sales[sales["market_code"] == m]
        if not row.empty and int(row["volume_2025"].iloc[0]) == 0:
            gaps.append(f"Vehicle is not sold in {MARKETS[m]} (0 units 2025) - requirements for {m} would be market-entry assumptions.")
    rest = comments[~comments["market"].isin(markets)]
    if len(rest):
        top = rest["country"].value_counts().head(3).to_dict()
        gaps.append(f"{len(rest)} verbatims come from outside the selected markets (e.g. {top}); they are excluded from market-specific counts.")
    return gaps


def sample_quotes(comments: pd.DataFrame, cls: pd.DataFrame, markets: list[str],
                  topics: list[str], per_topic: int = 6, max_len: int = 450) -> pd.DataFrame:
    """Representative verbatims per topic, preferring Wants / Defect / Difficult-to-use."""
    c = cls[cls["market"].isin(markets) & cls["topic"].isin(topics)]
    prio = {"Wants": 0, "Defect": 1, "Difficult to Use": 1, "Likes": 2}
    c = c.assign(p=c["feedback_type"].map(prio).fillna(3)).sort_values(["topic", "p"])
    picked = c.groupby("topic").head(per_topic)[["id", "topic", "feedback_type"]]
    out = picked.merge(comments[["id", "market", "engine", "text"]], on="id", how="left")
    out["text"] = out["text"].astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, max_len)
    return out


def build_insight_context(vehicle_name: str, markets: list[str], stats: pd.DataFrame, quotes: pd.DataFrame,
                          study: pd.DataFrame, sales: pd.DataFrame, gaps: list[str]) -> str:
    """Compact, fully-cited data package handed to Claude for insight synthesis."""
    parts = [f"# Vehicle: {vehicle_name}", f"# Markets in scope: {', '.join(MARKETS[m] + ' (' + m + ')' for m in markets)}"]
    parts.append("\n## Known data gaps (must be respected)\n" + "\n".join(f"- {g}" for g in gaps or ["none detected"]))
    parts.append("\n## Sales volumes (units)\n" + sales.to_csv(index=False))
    parts.append("\n## Customer feedback topic statistics (unique comments per VFC topic)\n" + stats.head(40).to_csv(index=False))
    if not study.empty:
        s = study[study["market"].isin(markets)].copy()
        s["score"] = s["score"].round(1)
        parts.append("\n## Customer study 2025 (score normalised 0-100; reference as STUDY:<market>:<attribute>)\n"
                     + s.sort_values(["market", "score"]).to_csv(index=False))
    q = "\n".join(f"[{r.id}] ({r.market}, {r.engine}, {r.topic}, {r.feedback_type}) {r.text}" for r in quotes.itertuples())
    parts.append("\n## Sample customer verbatims (reference by the ID in brackets)\n" + q)
    return "\n".join(parts)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def verify_evidence(evidence: list[dict], comments: pd.DataFrame, study: pd.DataFrame) -> list[dict]:
    """Mark each evidence item verified / unverified against the actual data.

    feedback: ID must exist; if a quote is given, it must appear in that comment.
    customer_study: attribute must exist for that market.
    Other source types cannot be checked locally and are marked 'external' / 'assumption'.
    """
    by_id = dict(zip(comments["id"], comments["text"].astype(str)))
    study_keys = {(_norm(a), m) for a, m in zip(study["attribute"], study["market"])} if not study.empty else set()
    out = []
    for e in evidence:
        e = dict(e)
        st = e.get("source_type")
        if st == "feedback":
            text = by_id.get(e.get("ref", "").strip())
            if text is None:
                e["verification"] = "unverified: ID not found in dataset"
            else:
                quote = _norm(e.get("detail", ""))
                snippet = quote[:60]
                e["verification"] = "verified" if not snippet or snippet in _norm(text) else "partially verified: ID exists, quote paraphrased"
        elif st == "customer_study":
            ref = e.get("ref", "")
            parts = ref.split(":", 2)
            ok = len(parts) == 3 and (_norm(parts[2]), parts[1].strip().upper()) in study_keys
            e["verification"] = "verified" if ok else "unverified: study attribute not found"
        elif st == "sales":
            e["verification"] = "verified (sales table)"
        elif st == "web":
            e["verification"] = "external source"
        else:
            e["verification"] = "assumption / not verifiable"
        out.append(e)
    return out


def evidence_strength(evidence: list[dict]) -> float:
    """0-1 score from verified evidence volume and source diversity (deterministic)."""
    verified = [e for e in evidence if str(e.get("verification", "")).startswith(("verified", "partially", "external"))]
    if not verified:
        return 0.0
    n = len(verified)
    diversity = len({e["source_type"] for e in verified})
    unverified_penalty = 0.15 * (len(evidence) - n)
    return max(0.0, min(1.0, 0.12 * min(n, 6) + 0.12 * min(diversity, 3) - unverified_penalty))
