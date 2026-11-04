# Learn by running the workflow

Complete the README setup first. Each exercise has a result you can verify.

## 1. Trace one grounded answer

Ask “Python automation” in the browser. Follow `api.py:question` to `knowledge.py:answer`, then `search`. Compare the returned source IDs with `voice_ai_lab/data/knowledge.json`.

**Verify:** the response contains only the matched course facts. The API labels the result `simulation`. `retrieval_ms` times local lookup only; it is not end-to-end voice latency.

**Try:** ask “xyzzy”, then “بايثون”. Unknown text returns no match. The Arabic keyword finds a course, but the deterministic formatter does not translate the response.

## 2. Understand the success boundary

Save a fictional learner. Follow `models.py:LeadInput` to `store.py:Store.capture`.

The API validates the schema and consent, checks the retry key, inserts the lead and a telemetry event in one transaction, commits, and only then returns a persisted receipt. There is no email or CRM side effect.

**Verify:** restart the API and refresh the dashboard. The row survives.

**Try:** uncheck consent or use a real email domain. Validation rejects the request before it reaches persistence.

## 3. Fail a new write

Follow the README's `LAB_FAIL_WRITES` drill. The important outcome is an honest failure, not a convincing assistant response.

**Verify:** HTTP 503, zero new rows, and no new success receipt. Restore writes, retry the same request, and confirm one row.

Read `test_transaction_rolls_back_if_event_write_fails`: the test drops the event table in a temporary database. Even though the lead insert occurs first, the failed event insert rolls back the whole transaction.

## 4. Make retries safe

Submit the same form twice. The UI reuses a UUID for unchanged details in the current page. The database has a UNIQUE constraint on that request ID and stores a hash of the payload.

**Verify:** first response 201, replay 200, same lead ID. Reuse that request ID with different details in a test and expect 409. Read the concurrency test to see multiple simultaneous retries create one row.

This is request-level idempotency, not global email deduplication. A new page, new voice session, or new request ID may intentionally create another record. Design a separate business duplicate policy before adapting this to real leads.

## 5. Add one fictional course

Add a record to `data/knowledge.json` with a unique ID and keywords. Add a test for a relevant question and an irrelevant question. Restart the app because the catalog is loaded on import.

**Verify:** the catalog, form dropdown, API validation, and retrieval agree on the new ID.

## 6. Add optional real voice

Read `docs/voice-mode.md`. Use your own small, isolated provider project. Do not use customer data. Inspect `build_agent` to see how function tools reuse the same retrieval and persistence code.

**Verify manually:** the agent discloses it is AI, looks up facts, asks consent, and reports a save only after `persisted=true`. Repeat with simulated writes failing. Prompt instructions influence behavior; they do not prove the model will always follow the workflow.

## 7. Measure before optimizing

Create a fixed scenario set: course question, policy question, unknown question, valid capture, missing consent, repeated capture, and write failure. Review answers against the fictional knowledge file.

For live audio, instrument caller speech-end and agent first-audio on the same audio timeline, group by model/language/tool use, and report median, p95, failures, and sample count. Reconcile cost from provider usage. These are future exercises; this starter does not claim an audio latency or cost baseline.

Only add a vector database after showing that keyword retrieval misses important questions. Only add an external mirror after you can test its failure and recovery paths without corrupting the primary result.
