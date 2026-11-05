"""Optional SDK smoke tests. No model session or audio device is started."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from voice_ai_lab.evidence import SessionRecorder
from voice_ai_lab.store import Store

pytest.importorskip("livekit.agents", reason="Install the voice extra for SDK smoke tests")

from voice_ai_lab.voice import build_agent  # noqa: E402


def test_voice_tools_share_validation_and_persistence(settings):
    async def scenario():
        store = Store(settings.db_path)
        store.initialize()
        agent = build_agent(store)
        known = await agent.search_knowledge("Python automation")
        assert known["matches"][0]["id"] == "python-automation"
        assert (await agent.search_knowledge("xyzzy"))["matches"] == []
        denied = await agent.save_test_lead(
            "Demo Learner", "demo@example.com", "voice-agents", False
        )
        assert denied["persisted"] is False
        assert store.leads(20, 0)[1] == 0
        saved = await agent.save_test_lead("Demo Learner", "demo@example.com", "voice-agents", True)
        replay = await agent.save_test_lead(
            "Demo Learner", "demo@example.com", "voice-agents", True
        )
        assert saved["persisted"] is True
        assert replay["replayed"] is True
        assert saved["id"] == replay["id"]

    asyncio.run(scenario())


def test_voice_tool_does_not_claim_failed_save(settings):
    async def scenario():
        store = Store(settings.db_path, fail_writes=True)
        store.initialize()
        agent = build_agent(store)
        result = await agent.save_test_lead(
            "Demo Learner", "demo@example.com", "voice-agents", True
        )
        assert result["persisted"] is False
        assert store.leads(20, 0)[1] == 0

    asyncio.run(scenario())


def test_final_sdk_metrics_export_is_content_free_and_not_double_counted(settings):
    from livekit.agents.llm import ChatMessage
    from livekit.agents.metrics.usage import AgentSessionUsage, LLMModelUsage

    recorder = SessionRecorder()
    session = SimpleNamespace(
        history=SimpleNamespace(
            items=[
                ChatMessage(role="user", content=["private caller details"]),
                ChatMessage(
                    role="assistant",
                    content=["private response"],
                    metrics={"e2e_latency": 1.25, "provider_request_ids": ["private-request"]},
                ),
            ]
        ),
        usage=AgentSessionUsage(
            model_usage=[LLMModelUsage(provider="openai", model="test-model", input_tokens=100)]
        ),
    )
    first = recorder.snapshot(session)
    second = recorder.snapshot(session)
    assert first.assistant_messages[0].sdk_e2e_ms == 1250
    assert first.usage_totals["llm_usage.input_tokens"] == 100
    assert second.usage_totals == first.usage_totals
    assert "private" not in first.model_dump_json()
    assert "test-model" not in first.model_dump_json()

    async def scenario():
        store = Store(settings.db_path, fail_writes=True)
        store.initialize()
        agent = build_agent(store, recorder)
        result = await agent.save_test_lead(
            "Demo Learner", "demo@example.com", "voice-agents", True
        )
        assert result["persisted"] is False
        assert recorder.tools[-1].success is False
        assert "demo@example.com" not in json.dumps(recorder.tools[-1].model_dump())

    asyncio.run(scenario())
