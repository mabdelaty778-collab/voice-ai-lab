"""Inspectable keyword retrieval. No embeddings or model API calls."""

import json
import re
import unicodedata
from importlib.resources import files

KNOWLEDGE = json.loads(
    files("voice_ai_lab").joinpath("data/knowledge.json").read_text(encoding="utf-8")
)
COURSES = {course["id"]: course for course in KNOWLEDGE["courses"]}
STOP_WORDS = {"a", "an", "the", "i", "is", "are", "do", "does", "can", "of", "to", "in", "and"}


def tokenize(text: str) -> set[str]:
    """Normalize spelling, not meaning; this is not translation or semantic retrieval."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    return set(re.findall(r"[^\W_]+", text)) - STOP_WORDS


def retrieve(query: str, limit: int = 3) -> list[dict]:
    """Expose overlap scores as counts, never as calibrated confidence probabilities."""
    if limit < 1:
        return []
    tokens = tokenize(query)
    ranked = []
    for kind, items in (("course", KNOWLEDGE["courses"]), ("faq", KNOWLEDGE["faqs"])):
        for item in items:
            keywords = set().union(*(tokenize(word) for word in item["keywords"]))
            matched = sorted(tokens & keywords)
            if matched:
                ranked.append(
                    {
                        "item": {"kind": kind, **item},
                        "score": len(matched),
                        "matched_terms": matched,
                    }
                )
    ranked.sort(key=lambda hit: (-hit["score"], hit["item"]["id"]))
    return ranked[:limit]


def search(query: str, limit: int = 3) -> list[dict]:
    """Return only items with a meaningful keyword hit; unknowns return no matches."""
    return [hit["item"] for hit in retrieve(query, limit)]


def answer(query: str) -> dict:
    hits = retrieve(query)
    matches = [hit["item"] for hit in hits]
    trace = {
        "method": "normalized-keyword-overlap-v1",
        "normalized_terms": sorted(tokenize(query)),
        "hits": [
            {
                "source_id": hit["item"]["id"],
                "score": hit["score"],
                "matched_terms": hit["matched_terms"],
            }
            for hit in hits
        ],
        "decision": "return_sources" if hits else "abstain",
    }
    if not matches:
        return {
            "reply": "I could not find that in the sample knowledge. "
            "Please clarify or ask a human.",
            "sources": [],
            "trace": trace,
        }
    lines = []
    for item in matches:
        if item["kind"] == "course":
            lines.append(
                f"{item['name']}: {item['duration']}; {item['price']}. "
                f"Prerequisites: {item['prerequisites']}. {item['summary']}"
            )
        else:
            lines.append(item["answer"])
    return {
        "reply": "\n\n".join(lines),
        "sources": [item["id"] for item in matches],
        "trace": trace,
    }
