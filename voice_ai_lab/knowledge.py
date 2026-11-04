"""Inspectable keyword retrieval. No embeddings or model API calls."""

import json
import re
from importlib.resources import files

KNOWLEDGE = json.loads(files("voice_ai_lab").joinpath("data/knowledge.json").read_text())
COURSES = {course["id"]: course for course in KNOWLEDGE["courses"]}
STOP_WORDS = {"a", "an", "the", "i", "is", "are", "do", "does", "can", "of", "to", "in", "and"}


def search(query: str, limit: int = 3) -> list[dict]:
    """Return only items with a meaningful keyword hit; unknowns return no matches."""
    tokens = set(re.findall(r"[^\W_]+", query.casefold())) - STOP_WORDS
    ranked = []
    for kind, items in (("course", KNOWLEDGE["courses"]), ("faq", KNOWLEDGE["faqs"])):
        for item in items:
            score = len(tokens & set(item["keywords"]))
            if score:
                ranked.append((score, {"kind": kind, **item}))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [item for _, item in ranked[:limit]]


def answer(query: str) -> dict:
    matches = search(query)
    if not matches:
        return {
            "reply": "I could not find that in the sample knowledge. "
            "Please clarify or ask a human.",
            "sources": [],
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
    return {"reply": "\n\n".join(lines), "sources": [item["id"] for item in matches]}
