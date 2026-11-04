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
| Docker image / Compose runtime | Not executed locally: no Docker engine was available; a CI job is included |
| Paid model session, microphone, speech quality, audio latency, and cost | Not run; require a learner's own isolated provider key and audio devices |
| GitHub Actions runs | Configuration included; a passing remote run must be verified after publication |

The fresh free environment emits a Starlette warning that its `httpx` compatibility path is deprecated. Its HTTP tests pass. No production database, provider key, telephony gateway, or customer record was used.

This record describes a source snapshot. Re-run the checks after changing code, dependencies, or the knowledge file. Do not treat the local retrieval timer as an audio-latency benchmark.
