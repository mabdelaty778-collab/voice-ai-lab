# Architecture and code map

| File | Responsibility |
|---|---|
| `config.py` | Read explicit lab settings; require a generated lab key |
| `models.py` | Validate test contacts, explicit consent, known course, retry UUID |
| `knowledge.py` | Rank fictional keyword hits and reject no-match queries |
| `store.py` | Commit leads and metadata events atomically; replay safely |
| `api.py` | Authenticate local API requests and map failures to HTTP responses |
| `static/` | Render the simulation and receipts without storing keys or inserting user HTML |
| `voice.py` | Optional paid LiveKit / OpenAI Realtime function-tool integration |
| `tests/` | Exercise temporary databases with external network connections blocked |

## Design decisions

**Separate learning environment.** The project uses its own SQLite file and fictional catalog. It never reads Supabase, MySQL, CRM, GSM, or production environment variables. The `.env` loader preserves explicit shell settings. The Docker image does not contain `.env`.

**Observable success.** A lead and its `lead_saved` event are one transaction. Success means the commit completed. Exceptions return a failure rather than pretending a human team was notified. No callback or booking tool is advertised.

**Idempotency.** Each logical form submission has a UUID. An existing UUID with the same normalized payload returns the prior receipt. A different payload returns 409. `BEGIN IMMEDIATE` serializes writers before this check; the UNIQUE constraint is the final backstop. IDs are retained in browser memory or the voice session, not globally deduplicated by email.

**Small retrieval corpus.** Explicit keywords are simple enough to inspect. No-hit queries return no sources. This is not semantic RAG, prompt-injection immunity, or a multilingual quality benchmark.

**Async boundaries.** FastAPI's ordinary `def` handlers run blocking SQLite calls in its thread pool. The voice tool uses `asyncio.to_thread` to keep database work off the audio event loop.

**No borrowed production assets.** This project does not import the academy's source, prompts, policy corpus, static SDK bundle, or git history. The learning architecture is inspired by that work; the implementation and sample content here are new.

## HTTP contract

All `/api/v1/` endpoints require `X-Lab-Key`. Keys in URLs are not supported.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Public process liveness and simulation label; no database or contact data |
| `GET /api/v1/catalog` | Fictional courses |
| `POST /api/v1/questions` | Deterministic answer, source IDs, local retrieval time |
| `POST /api/v1/leads` | 201 committed new lead; 200 replay; 409 conflicting request ID; 422 invalid input; 503 unavailable persistence |
| `GET /api/v1/leads?limit=20&offset=0` | Bounded, authenticated local dashboard listing |
| `GET /api/v1/metrics` | Counts of persisted fictional leads and local retrieval requests |

## Deliberate limits

The key is one local operator credential, not per-user authentication. SQLite is appropriate for a single-machine lesson; it is not a multi-tenant architecture. There is no shared rate limiter, public signup, public voice-token endpoint, or production deployment script. Keep the service on loopback. For a public service, design identity, authorization, abuse controls, HTTPS, data retention, monitoring, and provider spend controls first.

The voice integration is opt-in, has no telephony, and does not run in the Docker image. It does not promise voicemail detection, silent-call billing control, provider failover, or live admissions-calendar availability.
