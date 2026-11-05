# Voice AI measurements: what I measured and how to reproduce it

I added a reproducible local benchmark and an opt-in session recorder so I can separate
implementation evidence, local performance, and production outcomes. This page records the
first local run; production voice latency, total cost, and business impact remain unmeasured.

## Measured local baseline

Run on **5 November 2026**, Python 3.12.14, Linux, temporary SQLite database. Ten lookup
warmups were excluded. The timer surrounds a full `TestClient.post` request, including the
in-process ASGI transport, application middleware, tool work, and SQLite work. It does not
include a TCP network hop, speech providers, a GSM gateway, or the caller's audio device.
Percentiles use nearest rank. These are observations on this host, not service objectives.

| Operation | Samples | p50 | p90 | p95 |
|---|---:|---:|---:|---:|
| Course lookup | 100 | 11.414 ms | 16.812 ms | 17.520 ms |
| Committed save | 100 | 10.602 ms | 16.050 ms | 16.839 ms |
| Idempotent replay | 100 | 7.679 ms | 10.766 ms | 11.895 ms |

All **300 sequential requests** returned the expected result. With **8 worker threads**, 32
retries of the same request produced exactly one committed record in a 285.753 ms batch.
A deliberately failed new write returned 503 without a success receipt. A new application
instance preserved the earlier records and successfully retried the failed write.
These checks demonstrate the lab's local transaction and retry behavior; they do not
establish a production call-success rate, 32 simultaneous calls, uptime, or maximum capacity.

The run made **zero provider calls** and incurred zero provider usage charges. Host cost was
not allocated, so total operating cost is unknown. [Raw aggregate run receipt](local-benchmark.json).

```bash
uv run --frozen --extra dev python scripts/benchmark_local.py --samples 100 --workers 8
```

The benchmark creates and removes its own temporary database. It does not load production
settings, contact external services, or use provider credentials. The ordinary test suite
also runs a smaller benchmark while socket connections are blocked. CI checks correctness;
it does not enforce host-dependent millisecond thresholds.

## Collect real voice measurements locally

The optional recorder uses the lab's locked **LiveKit Agents 1.8** API. Set the following in
the lab's local `.env`, after completing the normal optional voice setup:

```dotenv
LAB_MEASUREMENTS_DIR=.local/session-measurements
```

Then run `uv run --frozen --extra voice python -m voice_ai_lab.voice console`. This optional
voice session uses your own provider key and is billed normally. The recorder itself sends
no additional requests. It writes one JSON file at normal job shutdown, using a newly
generated UUID rather than a caller, participant, room, or CRM identifier. It only records:

- Final assistant-message SDK latency and interruption flags.
- Save-tool elapsed time and whether the shared store confirmed persistence.
- Final numeric usage totals, counted once per session.
- Session duration, environment/route/language labels, terminal-error coverage, and error counts.

It does not export transcripts, audio, names, phone numbers, email addresses, tool arguments,
provider request IDs, or exception messages. This describes this recorder's output only;
it does not change the SDK's or deployment platform's own logging/recording settings.
Raw receipts remain private under `.local`; publish only reviewed aggregate results.
Forced process termination can prevent a receipt from being written. Receipt counts therefore
need reconciliation against an independent session-attempt register before reporting reliability.

```bash
uv run --frozen python -m voice_ai_lab.evidence .local/session-measurements
```

The aggregate report separates environment, route, and language. Interrupted messages are
excluded from its latency distribution and counted separately. Messages with no SDK latency,
including greetings or unavailable measurements, remain missing. Terminal errors are not the
same thing as task failures; an error-free conversation does not establish a saved lead or sale.
Save-tool success is per invocation, including idempotent replays, rather than per unique lead.

**SDK latency is not remote audible latency.** The SDK measures from the end of caller speech
to the agent response; its normal playback reporting does not include transport to the remote
speaker. For a caller-experienced number, use a synchronized client-side or loopback audio
measurement with defined speech-end and first-audible-frame markers. Do not add unrelated
STT/LLM/TTS percentiles or treat missing Realtime component timers as zero.

## Reconcile costs and business outcomes

Keep a private mapping from the generated measurement UUID to the actual session and CRM
record. Export only the following CSV columns, in this order, into a local file:

```csv
session_id,qualified,converted,actual_cost_usd
```

Use `true`, `false`, or blank for the two outcome flags. Blank means unknown. An actual cost
of zero must be explicitly confirmed; otherwise leave it blank. Costs must be allocated USD
totals for that session, including provider usage, transport/telephony, and allocated hosting
where applicable. Reconcile cached/audio/text token rates and fixed charges to actual invoices
before filling that field. Numeric usage counters alone are not an invoice.

```bash
uv run --frozen python -m voice_ai_lab.evidence .local/session-measurements --outcomes .local/outcomes.csv
```

The analyzer rejects duplicate IDs and unmatched outcome rows. It reports observed outcome
denominators, actual-cost coverage, and the mean only across costed sessions. Partial cost
coverage must not be presented as the overall cost per call. The output has no session IDs.
Conversion is an observed association; an uplift claim requires a comparable baseline or
controlled experiment. Define qualified lead and converted sale with admissions first, then
use the same qualification rules, attribution window, and deduplication rules in both cohorts.

## Academy production integration status

I have read access to the reviewed academy source, which pins Agents 1.5.17. I have not
changed or deployed that application, accessed its live session database, or run paid calls.
The lab recorder must not be copied into that older SDK without a staging compatibility check.
Use the schema in `voice_ai_lab/evidence.py` to map an existing sanitized export, or adapt and
verify the recorder in a production-owned staging branch before enabling it.

The concrete collection plan is:

1. Trace a lead save to its primary committed receipt. Track dashboard-mirror and callback
   delivery receipts separately; the original production success wording is not sufficient proof.
2. Run the same disclosed synthetic scenarios for English/Arabic and each provider route:
   ordinary Q&A, no-match, consent, durable save, repeated request, injected failure, recovery,
   interruption, and disconnect. Record all attempted sessions, including startup failures.
3. Capture at least 30 measured replies per route for an initial descriptive latency comparison;
   treat this as a starting sample, not a claim of statistical precision. State missing/interrupted
   samples and add client audio timing when claiming caller-experienced latency.
4. Reconcile session IDs to provider invoices and confirmed CRM outcomes. Report sample size,
   time window, route, language, SDK/model version, and test conditions alongside every claim.
5. Publish reviewed aggregate observations. Keep raw receipts, call recordings, the ID mapping,
   customer records, and invoices private. Source review and a local benchmark do not supply
   production outcomes.

Official measurement definitions checked on 5 November 2026:
[LiveKit data hooks and per-turn metrics](https://docs.livekit.io/testing/observability/data/).
The SDK integration is smoke-tested offline with real SDK message and usage objects;
microphone, provider, and production runs are still required to validate live collection.
