"""Optional SDK smoke tests. No model session or audio device is started."""

import asyncio

import pytest

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
