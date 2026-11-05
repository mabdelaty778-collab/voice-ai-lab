# Validation record

Checked on **4 November 2026**, using Python 3.12.14 and uv 0.13.5.

| Check | Result |
|---|---|
| Full local suite with optional voice SDK installed | 36 passed; tests blocked external socket connections |
| Fresh, hash-locked pip installation without voice SDK | 34 passed; optional voice test module skipped |
| Running Uvicorn HTTP smoke | Page, health, authentication, retrieval, durable save, and replay passed |
| Ruff lint and formatting | Passed |
| Frontend JavaScript syntax | Passed with `node --check` |
| Compose and GitHub Actions YAML | Parsed; loopback port and network-disabled test container settings checked |
| LiveKit SDK imports, tool invocation, and console CLI help | Passed without provider calls |
| Docker image / Compose runtime | Passed in GitHub Actions: isolated container tests, image startup, and health check |
| Automated HTTP walkthrough | Passed: isolated storage, source lookup, no-match behavior, durable save, retry, failed write, and recovery |
| Paid model session, microphone, speech quality, audio latency, and cost | Not run; require a learner's own isolated provider key and audio devices |
| GitHub Actions run 41878560510 | All four jobs passed: Python 3.11, Python 3.12, Docker, and optional voice SDK tools |

The fresh free environment emits a Starlette warning that its `httpx` compatibility path is deprecated. Its HTTP tests pass. No production database, provider key, telephony gateway, or customer record was used. [Verified CI run](https://github.com/mabdelaty778-collab/voice-ai-lab/actions/runs/41878560510). The new walkthrough was also executed locally; its CI execution can be checked on subsequent commits.

This record describes a source snapshot. Re-run the checks after changing code, dependencies, or the knowledge file. Do not treat the local retrieval timer as an audio-latency benchmark.

## Measurement update — 5 November 2026

The full local suite with the locked optional SDK passes **49 tests** with socket connections blocked. Ruff lint and formatting pass. Tests cover missing values, percentile tails, interrupted replies, environment separation, duplicate IDs, partial cost coverage, strict outcome flags, private-field rejection, final SDK metric extraction, and failed save receipts. No new dependency was added.

The local benchmark completed 300 sequential requests, 32 concurrent retries of one request, an injected write failure, and restart/recovery checks. Its latency figures measure in-process ASGI/SQLite only; [method and aggregate receipt](measurements.md). Live provider audio timing, actual total cost, and CRM conversion results remain unmeasured.
