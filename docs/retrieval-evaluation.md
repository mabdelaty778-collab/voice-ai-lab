# English / Arabic retrieval evaluation

This extension makes the lab's keyword retrieval inspectable. It does not add an LLM,
embeddings, translation, or speech. Replies still quote the English fictional catalog.

## Reproduce

After installing the pinned development dependencies:

```bash
python -m scripts.evaluate_retrieval --output .local/retrieval-report.json
pytest
ruff check .
ruff format --check .
```

The [published JSON report](retrieval-report.json) includes every query, expected source,
ranking, score, matched terms, failure, and SHA-256 fingerprints of the corpus, fixtures,
and retrieval code (UTF-8 text with LF newlines, consistent across platforms). Scores count overlapping terms; they are not confidence probabilities.
The API returns the same retrieval trace. Queries are not added to the metrics database.

## Method and limitations

- 60 hand-authored synthetic regression cases: 30 English, 30 Arabic; 52 answerable,
  8 expected abstentions. These were authored alongside the change, **not held out**.
- Compare the original case-folded keyword algorithm against Unicode NFKC normalization,
  Arabic diacritic/tatweel removal, alef normalization and final ya normalization.
- Use the same six-document fictional catalog and stable source-ID tie ordering.
- Hit@1 and MRR@3 use the 52 answerable queries. Abstention accuracy uses the 8
  unanswerable queries. Combined passes require either the expected top source or abstention.
- This small, deliberately spelling-focused set is not evidence of general RAG quality,
  dialect understanding, production accuracy, latency, cost, or voice performance.

The recorded run improves combined passes from **40/60 to 54/60**. Answerable Hit@1
is **48/52**; correct abstentions are **6/8**. All six remaining failures are public:
four paraphrases have no keyword hit, and two unrelated hospital questions collide
with generic location keywords. Normalization does not fix those semantic weaknesses.

Before using retrieval for real decisions, expand the corpus, collect a separate held-out
set, evaluate semantic/hybrid retrieval and reranking, and check unsupported-answer
behavior. A high keyword-overlap score alone should never authorize an external action.

The test network guard permits literal loopback connections for Windows asyncio's
socketpair implementation and blocks external connections. Tests use temporary databases.
