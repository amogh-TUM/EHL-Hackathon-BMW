"""Smoke tests for the deterministic layers. Run: .venv/Scripts/python -m pytest -q  (or python tests/test_core.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core import data_loader as dl  # noqa: E402
from src.core.evidence import coverage_report, evidence_strength, sample_quotes, topic_stats, verify_evidence  # noqa: E402
from src.core.scoring import factor_table, score, sensitivity  # noqa: E402


def test_feedback_dedup():
    comments, cls = dl.load_feedback("G60")
    assert comments["id"].is_unique
    assert len(comments) == 4000
    assert not cls["topic"].eq("no_class_found").any()


def test_study_parsing():
    s = dl.study_for_vehicle("G70")
    assert set(s["market"]) == {"CN", "EU", "US"}
    assert s["score"].between(0, 100).all()
    us = dl.load_study_us()
    assert "Overall exterior styling" in set(us["attribute"])


def test_gaps_flag_missing_china_feedback():
    comments, _ = dl.load_feedback("G70")
    gaps = coverage_report(comments, ["CN"], dl.study_for_vehicle("G70"), dl.load_sales()["G70"])
    assert any("No customer feedback" in g for g in gaps)


def test_f70_not_sold_in_us():
    comments, _ = dl.load_feedback("F70")
    gaps = coverage_report(comments, ["US"], dl.study_for_vehicle("F70"), dl.load_sales()["F70"])
    assert any("not sold" in g for g in gaps)


def test_verification():
    comments, cls = dl.load_feedback("G60")
    study = dl.study_for_vehicle("G60")
    real = comments.iloc[0]
    ev = verify_evidence([
        {"source_type": "feedback", "ref": real["id"], "detail": str(real["text"])[:40], "market": "US", "supports": True},
        {"source_type": "feedback", "ref": "G60-9999", "detail": "made up", "market": "US", "supports": True},
        {"source_type": "customer_study", "ref": "STUDY:EU:Value for money", "detail": "", "market": "EU", "supports": True},
    ], comments, study)
    assert ev[0]["verification"] == "verified"
    assert ev[1]["verification"].startswith("unverified")
    assert ev[2]["verification"] == "verified"
    assert 0 <= evidence_strength(ev) <= 1


def test_scoring_and_sensitivity():
    j = lambda s: {"score": s, "justification": "x"}  # noqa: E731
    reqs = [{"id": f"REQ-{i}", "title": f"t{i}",
             "ai": {"customer_impact": j(i % 5 + 1), "future_relevance": j(5 - i % 5), "competitive_gap": j(3)},
             "computed": {"voice_volume_raw": 10 * i, "market_volume": 0.3, "evidence_strength": 0.5}} for i in range(1, 6)]
    ft = factor_table(reqs)
    s = score(ft, {"customer_impact": 1, "voice_volume": 1, "market_volume": 1,
                   "future_relevance": 1, "competitive_gap": 1, "evidence_strength": 1})
    assert s["priority_score"].between(0, 100).all()
    assert len(sensitivity(ft)) == 5


def test_quote_sampling():
    comments, cls = dl.load_feedback("G70")
    stats = topic_stats(comments, cls, ["US"])
    q = sample_quotes(comments, cls, ["US"], stats["topic"].head(5).tolist())
    assert len(q) > 0 and q["text"].str.len().max() <= 450


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
