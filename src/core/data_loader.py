"""Deterministic loading and normalisation of the BMW-provided datasets (no AI here)."""
from __future__ import annotations

import logging

import pandas as pd
from pypdf import PdfReader

from .config import COUNTRY_TO_MARKET, DATA_RAW, SALES_FILE, STUDY_FILE, VEHICLES

logging.getLogger("pypdf").setLevel(logging.ERROR)  # BMW fonts trigger harmless warnings

US_SCALE = ["I Hate It", "A Failure", "Unsatisfactory", "Satisfactory", "Excellent", "Delightful", "I Love It"]


def _market(country: str) -> str:
    return COUNTRY_TO_MARKET.get(str(country).upper(), "RoW")


def load_feedback(vehicle: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (comments, classifications).

    The raw file has one row per (comment, classification), so a comment with three
    classifications appears three times. We split it into one row per comment and a
    separate long table of its classifications.
    """
    df = pd.read_excel(DATA_RAW / VEHICLES[vehicle]["feedback"])
    df = df.rename(columns={
        "ID": "id", "Source": "source", "Country": "country", "Engine Type": "engine",
        "Feedback Type": "feedback_type", "Customer Feedback": "text",
        "Vfc level2 Name": "topic", "Vfc level3 Name": "subtopic",
    })
    df["market"] = df["country"].map(_market)

    # Note: not .agg(engine=...) - 'engine' collides with pandas' own agg(engine=) keyword.
    comments = (
        df.groupby("id", sort=False)[["source", "country", "market", "engine", "text"]]
        .first()
        .reset_index()
    )
    cls = df[df["topic"].notna() & (df["topic"] != "no_class_found")]
    cls = cls[["id", "market", "engine", "feedback_type", "topic", "subtopic"]].drop_duplicates()
    return comments, cls


def load_sales() -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(DATA_RAW / SALES_FILE)
    out = {}
    for v, cfg in VEHICLES.items():
        s = xl.parse(cfg["sales_sheet"])
        s["growth_25_30_pct"] = ((s["volume_2030"] / s["volume_2025"].replace(0, pd.NA)) - 1) * 100
        out[v] = s
    return out


def load_study_cn_eu() -> pd.DataFrame:
    """Long table: attribute, market, model, mean (1-10 scale)."""
    raw = pd.read_excel(DATA_RAW / STUDY_FILE, sheet_name="CN_EU_2025", header=None)
    countries = raw.iloc[1, 1:].ffill()
    models = raw.iloc[2, 1:]
    rows, attr = [], None
    for i in range(2, len(raw)):
        label = raw.iloc[i, 0]
        if isinstance(label, str) and label.strip() != "Mean":
            attr = label.strip()
        elif label == "Mean" and attr:
            for col in raw.columns[1:]:
                val = raw.iloc[i, col]
                if pd.notna(val):
                    rows.append({"attribute": attr, "market": "CN" if countries[col] == "China" else "EU",
                                 "model": str(models[col]).strip(), "mean": float(val)})
    return pd.DataFrame(rows)


def load_study_us() -> pd.DataFrame:
    """Long table: attribute, model, top2 (Delightful+Love), bottom3 (Hate/Failure/Unsat), mean (1-7)."""
    raw = pd.read_excel(DATA_RAW / STUDY_FILE, sheet_name="US_2025", header=None)
    models = {c: str(raw.iloc[0, c]).strip() for c in raw.columns[2:]}
    rows, attr, dist = [], None, {}

    def flush():
        if attr and dist:
            for c, m in models.items():
                d = {k: v.get(c, 0.0) for k, v in dist.items()}
                total = sum(d.values()) or 1
                mean = sum((US_SCALE.index(k) + 1) * p for k, p in d.items()) / total
                rows.append({"attribute": attr, "model": m,
                             "top2": d.get("Delightful", 0) + d.get("I Love It", 0),
                             "bottom3": d.get("I Hate It", 0) + d.get("A Failure", 0) + d.get("Unsatisfactory", 0),
                             "mean": mean})

    # Row 0 holds the first question label alongside the model names, so start there.
    for i in range(len(raw)):
        label = raw.iloc[i, 0]
        if isinstance(label, str) and pd.isna(raw.iloc[i, 1]):
            flush()
            attr, dist = label.strip(), {}
        elif label in US_SCALE:
            dist[label] = {c: float(raw.iloc[i, c]) for c in models if pd.notna(raw.iloc[i, c])}
    flush()
    return pd.DataFrame(rows)


def study_for_vehicle(vehicle: str) -> pd.DataFrame:
    """Unified study view for one vehicle: attribute, market, score (0-100), raw metric."""
    cfg = VEHICLES[vehicle]
    frames = []
    cn_eu = load_study_cn_eu()
    for market, model in cfg["study_cn_eu"].items():
        part = cn_eu[(cn_eu["market"] == market) & (cn_eu["model"] == model)].copy()
        part["score"] = (part["mean"] - 1) / 9 * 100
        part["metric"] = part["mean"].map(lambda m: f"mean {m:.2f}/10")
        frames.append(part[["attribute", "market", "score", "metric"]])
    if cfg["study_us"]:
        us = load_study_us()
        part = us[us["model"] == cfg["study_us"]].copy()
        part["market"] = "US"
        part["score"] = (part["mean"] - 1) / 6 * 100
        part["metric"] = part.apply(lambda r: f"mean {r['mean']:.2f}/7, top-2 {r['top2']:.0%}, bottom-3 {r['bottom3']:.0%}", axis=1)
        frames.append(part[["attribute", "market", "score", "metric"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["attribute", "market", "score", "metric"])


def load_option_list_text(vehicle: str, max_chars: int = 60000) -> str:
    """German price/equipment list as plain text, used to know what is already offered."""
    reader = PdfReader(DATA_RAW / VEHICLES[vehicle]["options"])
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    return text[:max_chars]
