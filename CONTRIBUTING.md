# Contributing

Small, teachable improvements are welcome. Explain the learner-facing problem and include a focused regression test for changed behavior.

1. Create a branch.
2. Run `uv sync --frozen --extra dev`.
3. Make the change using fictional content only.
4. Run `uv run --frozen --extra dev pytest`, `uv run --frozen --extra dev ruff check .`, and `uv run --frozen --extra dev ruff format --check .`.
5. Open a pull request describing the behavior, validation, and any limitation.

For a dependency change, update `pyproject.toml`, run `uv lock`, and regenerate both pip exports:

```bash
uv export --frozen --no-dev --no-emit-project --output-file requirements.lock
uv export --frozen --no-dev --extra dev --no-emit-project --output-file requirements-dev.lock
```

Do not commit `.env`, databases, API keys, transcripts, private academy documents, or customer information. Do not enable paid model calls in default tests. Contributions are under the repository's MIT license.
