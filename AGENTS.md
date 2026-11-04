# Working on Voice AI Lab

- Keep the default app local, deterministic, and free of external service calls.
- Use only the fictional catalog and synthetic contacts. Never copy production settings, prompts, or databases.
- Never return a successful persistence result before a committed write.
- Preserve request-level idempotency and explicit no-match retrieval behavior.
- Keep blocking database work out of the voice event loop.
- Put optional paid voice dependencies behind the `voice` extra and explicit opt-in.
- Test with temporary SQLite databases and blocked external network access.
- Run pytest, Ruff checks, and Ruff formatting before publishing code.
- Update the lock and pip exports together after changing dependencies.
- Keep README instructions accurate about simulation, real audio, and verified versus unverified behavior.
