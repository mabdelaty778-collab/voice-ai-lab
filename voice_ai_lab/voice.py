"""Optional paid voice console. No telephony or CRM integration is included."""

import asyncio
import logging
import os
import time
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from voice_ai_lab.config import Settings
from voice_ai_lab.evidence import SessionRecorder, write_session
from voice_ai_lab.knowledge import search
from voice_ai_lab.models import LeadInput
from voice_ai_lab.store import PersistenceUnavailable, RequestConflict, Store


def build_agent(store: Store, recorder: SessionRecorder | None = None):
    # Lazy imports keep the free simulation independent of audio SDKs.
    from livekit.agents import Agent, function_tool

    class LearningAdvisor(Agent):
        def __init__(self):
            super().__init__(
                instructions=(
                    "You are an AI voice advisor in a fictional learning lab. "
                    "Disclose that you are AI. Use search_knowledge for every course, "
                    "price, policy, and accreditation answer. If there are no matching sources, "
                    "say you do not know and ask for clarification. "
                    "Never invent a course, price, booking, payment, or real certification. "
                    "Use fictional names and example.com email addresses only. Ask for explicit "
                    "consent before save_test_lead. "
                    "It records interest, not an enrollment or booking. "
                    "Confirm a save only if the tool returns persisted=true. "
                    "On a write failure say nothing was saved and offer to retry. "
                    "Reply briefly in the caller's language."
                )
            )
            # A retry within the session uses the same key for the same logical payload.
            self._request_ids: dict[tuple, str] = {}

        @function_tool()
        async def search_knowledge(self, query: str) -> dict:
            """Retrieve fictional course facts and policies; no matches means unknown."""
            if not query.strip() or len(query) > 500:
                return {"matches": [], "error": "Ask a short, specific course question."}
            return {"matches": search(query)}

        @function_tool()
        async def save_test_lead(
            self, name: str, email: str, course_id: str, consent: bool
        ) -> dict:
            """Persist synthetic course interest after the caller explicitly agrees."""
            started = time.perf_counter()
            persisted = False
            key = (name.strip(), email.strip().lower(), course_id)
            request_id = self._request_ids.setdefault(key, str(uuid4()))
            try:
                lead = LeadInput(
                    name=name,
                    email=email,
                    course_id=course_id,
                    consent=consent,
                    request_id=request_id,
                )
                row, created = await asyncio.to_thread(store.capture, lead)
                persisted = True
                return {"persisted": True, "id": row["id"], "replayed": not created}
            except ValidationError:
                return {
                    "persisted": False,
                    "error": "Check consent, course ID and fictional contact details.",
                }
            except (PersistenceUnavailable, RequestConflict):
                return {"persisted": False, "error": "Nothing confirmed. Please retry."}
            finally:
                if recorder is not None:
                    recorder.tool("save_test_lead", started, persisted)

    return LearningAdvisor()


def main():
    settings = Settings.from_env()
    if os.getenv("LAB_ENABLE_VOICE", "false").lower() != "true":
        raise SystemExit(
            "Voice is opt-in. Set LAB_ENABLE_VOICE=true in .env; provider usage is billed."
        )
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise SystemExit("Set your own OPENAI_API_KEY for the optional paid voice mode.")

    from livekit import agents
    from livekit.agents import AgentSession
    from livekit.plugins import openai

    async def entrypoint(ctx: agents.JobContext):
        store = Store(settings.db_path, settings.fail_writes)
        store.initialize()
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                model=os.getenv("LAB_REALTIME_MODEL", "gpt-realtime"),
                voice=os.getenv("LAB_VOICE", "marin"),
            )
        )
        recorder = None
        measurements_dir = os.getenv("LAB_MEASUREMENTS_DIR", "").strip()
        if measurements_dir:
            recorder = SessionRecorder()

            @session.on("error")
            def on_error(event):
                recorder.provider_error_events += 1

            @session.on("close")
            def on_close(event):
                recorder.terminal_error = event.error is not None

            async def save_measurements():
                # The SDK has closed the session before shutdown callbacks run.
                # Read final metrics once, then write off the audio event loop.
                try:
                    record = recorder.snapshot(session, environment="lab", route="realtime")
                    await asyncio.to_thread(write_session, Path(measurements_dir), record)
                except (OSError, ValueError, AttributeError):
                    logging.getLogger(__name__).error(
                        "Session measurement export failed; no measurement receipt confirmed."
                    )

            ctx.add_shutdown_callback(save_measurements)

        await session.start(room=ctx.room, agent=build_agent(store, recorder))
        await session.generate_reply(
            instructions="Introduce yourself as an AI in a fictional lab "
            "and ask what course to explore."
        )

    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    main()
