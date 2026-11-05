# From voice conversation to reliable business tools

**Mohamed Abdelaty · AI Engineer / Software Engineer**

[Watch the redacted demo](https://github.com/mabdelaty778-collab/voice-ai-lab/blob/main/docs/clinic-voice-demo-redacted.mp4) · [Run the learning lab](../README.md#start-locally)

For the academy application's architecture, provider tradeoffs, and documented Arabic audio-framing incident, read the [production case study](production-case-study.md). This page describes the separate learning lab.

## Problem and ownership

I built two voice AI agents for clinic and academy use cases, with dashboards and connections to databases, CRM systems, and GSM/SIP infrastructure. The engineering challenge was connecting a natural conversation to business operations while keeping failures and persistence visible.

The attached clinic recording provides a concrete example of the conversational interface. I created Voice AI Lab as a separate open-source implementation so learners can inspect and reproduce the tool, storage, retry, and failure-handling patterns using fictional data.

## What I implemented in the public lab

| Concern | Implementation | Reason |
|---|---|---|
| Knowledge lookup | Deterministic keyword matching with source IDs and an explicit no-match result | Make retrieval behavior easy to inspect and test |
| Lead capture | Validated fictional contacts and explicit consent | Keep the exercise separate from real customer data |
| Persistence | SQLite transaction for the lead and its event | Return success only after a committed write |
| Retries | Request UUID, payload comparison, and database uniqueness | Replaying a request must not create a duplicate |
| Voice integration | Optional LiveKit console with OpenAI Realtime function tools | Exercise the same service layer with spoken input |
| Async boundaries | Database work moved off the voice event loop | Avoid blocking audio processing with synchronous storage |
| Failure behavior | Deliberate write-failure switch, rollback, and recovery exercises | Make the failure path observable and reproducible |
| Reproducibility | Locked dependencies, Docker, tests, and CI | Give learners an environment they can verify |

## Deliberate tradeoffs

The free lab uses keyword retrieval rather than a vector database because its catalog is small and its matching should be visible. SQLite keeps setup simple; this is a single-machine lesson, not a multi-tenant production service. Real voice is opt-in because it requires provider billing, network access, and audio hardware. Telephony and CRM integrations remain outside this teaching implementation.

## Evidence

| Claim | Evidence |
|---|---|
| A working conversational interface | [Redacted recording and timestamp guide](demo.md) |
| Durable writes, safe retries, and failure recovery in the lab | Automated tests and `scripts/demo_workflow.py` |
| Repeatable automated checks | [Validation record](validation.md) and [GitHub Actions](https://github.com/mabdelaty778-collab/voice-ai-lab/actions) |
| Production scale, audio latency, conversion uplift, and callback delivery | Not established by the recording or this lab; no numerical claims are made here |

The lab's recorded baseline is 36 passing tests with the optional voice SDK installed. That checks local tool behavior; it does not measure speech quality or verify a paid model session. See the validation record for the checked source snapshot and environment.

## Next engineering measurements

Before making production performance claims, collect time to first audible response across representative conversations, tool success and failure rates, duplicate-write rates, provider usage costs, and callback delivery receipts. Pair each measurement with its sample size, environment, and failure definition.

The distinction matters: an agent can speak a promise before a business action has happened. The public lab makes committed persistence and explicit failure part of the learning exercise.
