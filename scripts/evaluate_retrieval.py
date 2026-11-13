"""Reproducible offline retrieval evaluation; no model, network, or audio calls."""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from voice_ai_lab.knowledge import KNOWLEDGE, STOP_WORDS, answer

ROOT = Path(__file__).resolve().parents[1]


def baseline(query: str) -> list[str]:
    """Frozen pre-normalization algorithm on the same, unchanged sample corpus."""
    tokens = set(re.findall(r"[^\W_]+", query.casefold())) - STOP_WORDS
    hits = []
    for item in KNOWLEDGE["courses"] + KNOWLEDGE["faqs"]:
        score = len(tokens & set(item["keywords"]))
        if score:
            hits.append((score, item["id"]))
    return [source for _, source in sorted(hits, key=lambda row: (-row[0], row[1]))[:3]]


def summarize(rows: list[dict], field: str) -> dict:
    positives = [row for row in rows if row["expected"]]
    negatives = [row for row in rows if not row["expected"]]
    hit1 = sum(bool(r[field]) and r[field][0] in r["expected"] for r in positives)
    hit3 = sum(bool(set(r[field]) & set(r["expected"])) for r in positives)
    abstained = sum(not r[field] for r in negatives)
    reciprocal = sum(
        next((1 / (i + 1) for i, s in enumerate(r[field]) if s in r["expected"]), 0)
        for r in positives
    )
    return {
        "cases": len(rows),
        "answerable": len(positives),
        "unanswerable": len(negatives),
        "hit_at_1_count": hit1,
        "hit_at_3_count": hit3,
        "hit_at_1": round(hit1 / len(positives), 4) if positives else None,
        "mrr_at_3": round(reciprocal / len(positives), 4) if positives else None,
        "correct_abstentions": abstained,
        "abstention_accuracy": round(abstained / len(negatives), 4) if negatives else None,
        "passed": hit1 + abstained,
    }


def evaluate() -> dict:
    fixture = ROOT / "evals/retrieval-cases.json"
    corpus = ROOT / "voice_ai_lab/data/knowledge.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))["cases"]
    rows = []
    for case in cases:
        result = answer(case["query"])
        sources = result["sources"]
        passed = (
            (bool(sources) and sources[0] in case["expected"]) if case["expected"] else not sources
        )
        rows.append(
            {
                **case,
                "baseline": baseline(case["query"]),
                "candidate": sources,
                "passed": passed,
                "reply": result["reply"],
                "trace": result["trace"],
            }
        )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "Synthetic authored regression set, not held out. Keyword retrieval only; "
        "no LLM, embeddings, speech, real CRM, or production performance measured.",
        "method": "normalized-keyword-overlap-v1",
        "sha256": {
            "fixtures": hashlib.sha256(
                fixture.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest(),
            "corpus": hashlib.sha256(
                corpus.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest(),
            "retrieval_code": hashlib.sha256(
                (ROOT / "voice_ai_lab/knowledge.py").read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest(),
        },
        "summary": {
            language: {
                field: summarize(
                    [r for r in rows if language == "all" or r["language"] == language], field
                )
                for field in ("baseline", "candidate")
            }
            for language in ("all", "en", "ar")
        },
        "results": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".local/retrieval-report.json")
    args = parser.parse_args()
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {args.output}")
