# Optional real voice

The free browser lab teaches the tools and failure boundaries. This exercise adds a model and audio using LiveKit Agents' local console and the direct OpenAI plugin. It does not deploy a server or dial anyone.

## Setup

1. Complete and test the free lab.
2. Install the optional extra with `uv sync --frozen --extra dev --extra voice`.
3. Keep `LAB_DB_PATH=.local/lab.sqlite3` and the generated `LAB_API_KEY` in `.env`.
4. Add your own `OPENAI_API_KEY`, set `LAB_ENABLE_VOICE=true`, and choose an available Realtime model using `LAB_REALTIME_MODEL`.
5. On a machine with audio devices, run `uv run --frozen --extra voice python -m voice_ai_lab.voice console`.
6. Stop with Ctrl+C when finished, then set `LAB_ENABLE_VOICE=false` again.

Console mode uses local microphone/speakers rather than LiveKit media transport. Direct OpenAI usage still sends audio and tool context to the provider and incurs API charges. LiveKit Cloud keys are not used by the direct-plugin console path. Use fictional conversation content only. A ChatGPT subscription does not supply the application's API key.

## Try these scenarios

| Say | Check |
|---|---|
| “What does the Python automation course cover?” | A knowledge-tool call precedes the factual answer |
| “Is this a real accredited academy?” | It explains that the academy and credentials are fictional |
| “Can you save Demo Learner, learner@example.com, for voice-agents?” | It asks for explicit consent before attempting persistence |
| “Yes, save that fictional record.” | Tool returns a persisted receipt; refresh the local dashboard |
| Repeat the save in the same session | The tool replays the existing request rather than duplicating it |
| Try a new lead with `LAB_FAIL_WRITES=true` after restarting | No successful save is confirmed |

## Troubleshooting

- **Voice disabled:** this is intentional. Set both the opt-in flag and your own provider key.
- **Missing audio device / PortAudio:** run on a laptop, not a headless container. Linux may need the OS PortAudio package for microphone support.
- **Model unavailable or quota error:** check access and billing in your own provider project. Change the model ID only to one your project supports.
- **Dashboard row missing:** run the API and console from the same repository root and use the same `LAB_DB_PATH`. Docker data uses a separate named volume.
- **No answer for a valid question:** add explicit keywords or improve retrieval with tests. The lab intentionally rejects no-match questions.

## What has and has not been tested

For local, content-free measurements, optionally set
`LAB_MEASUREMENTS_DIR=.local/session-measurements` before starting the console. A private JSON
receipt is written at job shutdown using final SDK message metrics and cumulative usage.
See [measurement definitions, reconciliation, and evidence limits](measurements.md).

The free API, schema, persistence, and retry behavior can be tested without credentials. Optional SDK import and tool calls can also be smoke-tested without starting a model session. Successful import does not prove provider access, microphone behavior, latency, or model compliance. Run the scenario table with your own isolated key to validate those properties.

Official references, checked when preparing this starter:

- [LiveKit voice AI quickstart](https://docs.livekit.io/agents/start/voice-ai/)
- [OpenAI Realtime plugin](https://docs.livekit.io/agents/models/realtime/openai/)
- [Agent server startup modes](https://docs.livekit.io/agents/server/startup-modes/)

The example uses the Python `WorkerOptions` CLI compatibility interface supported by the locked SDK. LiveKit's current docs also describe the newer `lk agent` CLI. Keep SDK upgrades deliberate: update the lock, run tests, and recheck console startup.
