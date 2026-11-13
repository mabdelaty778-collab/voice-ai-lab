import json
from pathlib import Path

import pytest

from scripts.evaluate_retrieval import evaluate, summarize
from voice_ai_lab.knowledge import answer, search, tokenize


@pytest.mark.parametrize(
    "query,source",
    [
        ("أَتْمَتَة", "python-automation"),
        ("اتمتة", "python-automation"),
        ("إصطناعي", "ai-foundations"),
        ("ذَكَاء", "ai-foundations"),
        ("صوتى", "voice-agents"),
        ("بـايـثـون", "python-automation"),
        ("أَقْسَاط", "payments"),
        ("شَهَادَة", "certificates"),
        ("اونلاين", "delivery"),
        ("ＰＹＴＨＯＮ", "python-automation"),
    ],
)
def test_spelling_variants_retrieve_same_source(query, source):
    assert search(query)[0]["id"] == source


def test_trace_reports_evidence_without_fabricating_confidence(client, headers):
    result = client.post("/api/v1/questions", headers=headers, json={"text": "أَقْسَاط"}).json()[
        "data"
    ]
    assert result["trace"]["hits"] == [
        {"source_id": "payments", "score": 1, "matched_terms": ["اقساط"]}
    ]
    assert result["trace"]["decision"] == "return_sources"
    assert "confidence" not in result["trace"]
    assert answer("astronomy")["trace"]["decision"] == "abstain"


def test_normalization_and_ranking_boundaries():
    assert tokenize("أَتْمَتَة") == tokenize("اتمتة")
    assert search("python", limit=0) == []
    assert search("python", limit=-1) == []
    assert search("pythonic") == []
    # Stable ID ordering on tied scores, unchanged from the original retrieval contract.
    assert [r["id"] for r in search("voice python")] == ["python-automation", "voice-agents"]


def test_evaluation_counts_and_failures_remain_inspectable():
    report = evaluate()
    assert len({row["id"] for row in report["results"]}) == 60
    assert report["summary"]["en"]["candidate"]["cases"] == 30
    assert report["summary"]["ar"]["candidate"]["cases"] == 30
    # The authored set records weaknesses; it must not hide misses to advertise 100%.
    failures = {row["query"] for row in report["results"] if not row["passed"]}
    assert "where is the nearest hospital" in failures
    assert "ينفع ادفع على دفعات؟" in failures
    assert (
        report["summary"]["ar"]["candidate"]["passed"]
        > report["summary"]["ar"]["baseline"]["passed"]
    )
    fixture = Path(__file__).resolve().parents[1] / "evals/retrieval-cases.json"
    assert json.loads(fixture.read_text(encoding="utf-8"))["version"] == 1


def test_metrics_use_correct_denominators_and_rank():
    rows = [
        {"expected": ["a"], "candidate": ["x", "a"]},
        {"expected": ["b"], "candidate": ["b"]},
        {"expected": [], "candidate": []},
        {"expected": [], "candidate": ["x"]},
    ]
    metrics = summarize(rows, "candidate")
    assert metrics["hit_at_1"] == 0.5
    assert metrics["mrr_at_3"] == 0.75
    assert metrics["abstention_accuracy"] == 0.5
    assert metrics["passed"] == 2
