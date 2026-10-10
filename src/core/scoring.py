"""Transparent, deterministic prioritisation. AI judgements are inputs; the formula and weights are PM-owned."""
from __future__ import annotations

import pandas as pd

# origin tells the PM who produced each factor: computed from data, or judged by the AI.
FACTORS = {
    "customer_impact": {"label": "Customer impact", "origin": "AI-judged", "help": "Severity/value of the need for customers (1-5, AI with justification)."},
    "voice_volume": {"label": "Voice-of-customer volume", "origin": "Computed", "help": "Unique feedback comments on the linked VFC topics in the target markets, relative to the top requirement."},
    "market_volume": {"label": "Market volume 2030", "origin": "Computed", "help": "Share of the line's 2030 sales volume (EU+CN+US) covered by the target markets."},
    "future_relevance": {"label": "Future relevance (3-5 yrs)", "origin": "AI-judged", "help": "Expected importance at successor launch - forward-looking assumption."},
    "competitive_gap": {"label": "Competitive gap", "origin": "AI-judged", "help": "How far BMW lags or leads competitors on this need."},
    "evidence_strength": {"label": "Evidence strength", "origin": "Computed", "help": "Verified citations and source diversity; unverified citations reduce it."},
    "brand_fit": {"label": "BMW brand fit", "origin": "AI-judged", "help": "Fit with BMW brand pillars, from the evaluation engine (neutral 3/5 until evaluated)."},
}

DEFAULT_WEIGHTS = {"customer_impact": 25, "voice_volume": 15, "market_volume": 15,
                   "future_relevance": 15, "competitive_gap": 10, "evidence_strength": 10, "brand_fit": 10}

PRESETS = {
    "Balanced (default)": DEFAULT_WEIGHTS,
    "Customer voice first": {"customer_impact": 30, "voice_volume": 30, "market_volume": 10,
                             "future_relevance": 10, "competitive_gap": 5, "evidence_strength": 10, "brand_fit": 5},
    "Future-oriented": {"customer_impact": 15, "voice_volume": 5, "market_volume": 15,
                        "future_relevance": 35, "competitive_gap": 15, "evidence_strength": 5, "brand_fit": 10},
    "Volume-driven": {"customer_impact": 20, "voice_volume": 15, "market_volume": 40,
                      "future_relevance": 10, "competitive_gap": 5, "evidence_strength": 5, "brand_fit": 5},
    "Brand-led": {"customer_impact": 20, "voice_volume": 10, "market_volume": 10,
                  "future_relevance": 15, "competitive_gap": 10, "evidence_strength": 5, "brand_fit": 30},
}


def voice_volume_raw(topics: list[str], markets: list[str], cls: pd.DataFrame) -> int:
    c = cls[cls["topic"].isin(topics) & cls["market"].isin(markets)]
    return int(c["id"].nunique())


def market_volume(markets: list[str], sales: pd.DataFrame) -> float:
    core = sales[sales["market_code"].isin(["EU", "CN", "US"])]
    total = core["volume_2030"].sum()
    return float(core[core["market_code"].isin(markets)]["volume_2030"].sum() / total) if total else 0.0


def factor_table(reqs: list[dict]) -> pd.DataFrame:
    """reqs carry precomputed raw factors; normalise everything to 0-1."""
    rows = []
    max_voice = max([r["computed"]["voice_volume_raw"] for r in reqs] or [1]) or 1
    for r in reqs:
        a, c = r["ai"], r["computed"]
        rows.append({
            "id": r["id"], "title": r["title"],
            "customer_impact": (a["customer_impact"]["score"] - 1) / 4,
            "voice_volume": c["voice_volume_raw"] / max_voice,
            "market_volume": c["market_volume"],
            "future_relevance": (a["future_relevance"]["score"] - 1) / 4,
            "competitive_gap": (a["competitive_gap"]["score"] - 1) / 4,
            "evidence_strength": c["evidence_strength"],
            "brand_fit": ((r.get("evaluation") or {}).get("brand_fit", {}).get("score", 3) - 1) / 4,
        })
    return pd.DataFrame(rows)


def score(ft: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    weights = {f: weights.get(f, DEFAULT_WEIGHTS[f]) for f in FACTORS}  # older saved weights lack new factors
    total_w = sum(weights.values()) or 1
    out = ft.copy()
    for f in FACTORS:
        out[f"contrib_{f}"] = out[f].clip(0, 1) * weights.get(f, 0) / total_w * 100
    out["priority_score"] = out[[f"contrib_{f}" for f in FACTORS]].sum(axis=1).round(1)
    out["rank"] = out["priority_score"].rank(ascending=False, method="min").astype(int)
    return out.sort_values("rank")


def sensitivity(ft: pd.DataFrame) -> pd.DataFrame:
    """Rank of each requirement under every preset - shows how robust a priority is to weighting choices."""
    ranks = {name: score(ft, w).set_index("id")["rank"] for name, w in PRESETS.items()}
    df = pd.DataFrame(ranks)
    df["best_rank"] = df.min(axis=1)
    df["worst_rank"] = df.max(axis=1)
    df["robust"] = (df["worst_rank"] - df["best_rank"]) <= 2
    return df
