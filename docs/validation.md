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
