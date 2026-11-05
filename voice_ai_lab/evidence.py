"""Local, content-free session measurements and an offline aggregate report.

No transcripts, audio, contacts, room names, tool arguments, or provider request IDs
are collected. Unknown outcomes and costs stay unknown rather than becoming zero.
"""

import argparse
import csv
import json
import math
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssistantMeasurement(EvidenceModel):
    sdk_e2e_ms: NonNegative | None = None
    interrupted: StrictBool = False


class ToolMeasurement(EvidenceModel):
    name: Literal["search_knowledge", "save_test_lead"]
    elapsed_ms: NonNegative
    success: StrictBool


class SessionEvidence(EvidenceModel):
    schema_version: Literal[1] = 1
    session_id: UUID = Field(default_factory=uuid4)
    environment: Literal["lab", "staging", "production"] = "lab"
    route: Literal["realtime", "pipeline"] = "realtime"
    language: Literal["en", "ar", "hi", "ur", "mixed", "unspecified"] = "unspecified"
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: NonNegative
    terminal_error: StrictBool | None = None
    provider_error_events: int = Field(default=0, ge=0)
    assistant_messages: list[AssistantMeasurement] = Field(default_factory=list)
    tools: list[ToolMeasurement] = Field(default_factory=list)
    # Final cumulative snapshot only; never sum repeated usage-update events.
    usage_totals: dict[str, NonNegative] = Field(default_factory=dict)


class Outcome(EvidenceModel):
    session_id: UUID
    qualified: StrictBool | None = None
    converted: StrictBool | None = None
    # Allocated actual total cost, not a price guess or just LLM charges.
    actual_cost_usd: NonNegative | None = None


USAGE_FIELDS = (
    "input_tokens",
    "input_cached_tokens",
    "input_audio_tokens",
    "input_text_tokens",
    "output_tokens",
    "output_audio_tokens",
    "output_text_tokens",
    "characters_count",
    "audio_duration",
    "session_duration",
)


class SessionRecorder:
    """Opt-in recorder for the lab's installed LiveKit Agents 1.8 API.

    Inspect final message metrics at shutdown, when they have finished updating.
    The SDK's e2e timer is not a measurement at the remote caller's speaker.
    """

    def __init__(self):
        self.session_id = uuid4()
        self.started = time.perf_counter()
        self.tools: list[ToolMeasurement] = []
        self.terminal_error: bool | None = None
        self.provider_error_events = 0

    def tool(self, name: str, started: float, success: bool) -> None:
        self.tools.append(
            ToolMeasurement(
                name=name, elapsed_ms=(time.perf_counter() - started) * 1000, success=success
            )
        )

    def snapshot(self, session, **labels) -> SessionEvidence:
        messages = []
        for item in session.history.items:
            if getattr(item, "type", None) != "message" or item.role != "assistant":
                continue
            seconds = item.metrics.get("e2e_latency")
            messages.append(
                AssistantMeasurement(
                    sdk_e2e_ms=None if seconds is None else seconds * 1000,
                    interrupted=item.interrupted,
                )
            )
        usage = defaultdict(float)
        for model in session.usage.model_usage:
            # Numeric totals support reconciliation, not automatic billing estimates.
            for field in USAGE_FIELDS:
                value = getattr(model, field, None)
                if value is not None:
                    usage[f"{model.type}.{field}"] += value
        return SessionEvidence(
            session_id=self.session_id,
            duration_seconds=time.perf_counter() - self.started,
            terminal_error=self.terminal_error,
            provider_error_events=self.provider_error_events,
            assistant_messages=messages,
            tools=self.tools,
            usage_totals=dict(usage),
            **labels,
        )


def write_session(directory: Path, record: SessionEvidence) -> Path:
    """One file per session avoids concurrent processes appending to one JSONL file."""
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / f"{record.session_id}.json"
    # Refuse to overwrite: duplicate exports must be investigated, not counted twice.
    with target.open("x", encoding="utf-8") as stream:
        target.chmod(0o600)
        stream.write(record.model_dump_json(indent=2) + "\n")
    return target


def distribution(values: list[float]) -> dict:
    """Nearest-rank percentiles; retain n so tiny samples are obvious."""
    ordered = sorted(values)
    if not all(math.isfinite(value) and value >= 0 for value in ordered):
        raise ValueError("Measurements must be finite and nonnegative")
    result = {"n": len(ordered), "p50_ms": None, "p90_ms": None, "p95_ms": None}
    if ordered:
        for percentile in (50, 90, 95):
            result[f"p{percentile}_ms"] = round(
                ordered[math.ceil(len(ordered) * percentile / 100) - 1], 3
            )
    return result


def _rate(values: list[bool]) -> dict:
    return {
        "observed": len(values),
        "positive": sum(values),
        "rate": sum(values) / len(values) if values else None,
    }


def summarize(records: list[SessionEvidence], outcomes: list[Outcome] | None = None) -> dict:
    ids = [record.session_id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate session IDs in measurement inputs")
    outcomes = outcomes or []
    by_id = {outcome.session_id: outcome for outcome in outcomes}
    if len(by_id) != len(outcomes):
        raise ValueError("Duplicate outcome rows")
    if set(by_id) - set(ids):
        raise ValueError("An outcome has no matching measured session")
    buckets = defaultdict(list)
    for record in records:
        buckets[(record.environment, record.route, record.language)].append(record)
    groups = []
    for (environment, route, language), sessions in sorted(buckets.items()):
        messages = [m for s in sessions for m in s.assistant_messages]
        tools = [tool for s in sessions for tool in s.tools]
        saves = [tool.success for tool in tools if tool.name == "save_test_lead"]
        matched = [by_id[s.session_id] for s in sessions if s.session_id in by_id]
        costed = [o for o in matched if o.actual_cost_usd is not None]
        costs = [o.actual_cost_usd for o in costed]
        groups.append(
            {
                "environment": environment,
                "route": route,
                "language": language,
                "sessions": len(sessions),
                "sdk_response_latency": distribution(
                    [
                        m.sdk_e2e_ms
                        for m in messages
                        if not m.interrupted and m.sdk_e2e_ms is not None
                    ]
                ),
                "assistant_messages": len(messages),
                "interrupted_messages_excluded": sum(m.interrupted for m in messages),
                "messages_without_latency": sum(m.sdk_e2e_ms is None for m in messages),
                "tool_latency": distribution([tool.elapsed_ms for tool in tools]),
                "committed_save_attempts": _rate(saves),
                "terminal_errors": _rate(
                    [s.terminal_error for s in sessions if s.terminal_error is not None]
                ),
                "provider_error_events": sum(s.provider_error_events for s in sessions),
                "crm_qualified": _rate([o.qualified for o in matched if o.qualified is not None]),
                "crm_converted": _rate([o.converted for o in matched if o.converted is not None]),
                "cost": {
                    "currency": "USD",
                    "sessions_with_actual_cost": len(costs),
                    "coverage": len(costs) / len(sessions),
                    "known_total_usd": round(sum(costs), 6) if costs else None,
                    "mean_per_costed_session_usd": round(statistics.mean(costs), 6)
                    if costs
                    else None,
                },
            }
        )
    return {
        "schema_version": 1,
        "scope": "observed sessions only; no uptime, capacity, or causal uplift claim",
        "latency_method": "SDK e2e metric; nearest-rank; interrupted messages excluded",
        "groups": groups,
    }


def load_outcomes(path: Path) -> list[Outcome]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["session_id", "qualified", "converted", "actual_cost_usd"]:
            raise ValueError("Unexpected outcome CSV columns")
        outcomes = []
        for row in reader:
            values = {key: value.strip() for key, value in row.items()}
            for key in ("qualified", "converted"):
                raw = values[key].lower()
                if raw not in ("", "true", "false"):
                    raise ValueError("Outcome flags must be blank, true, or false")
                values[key] = None if not raw else raw == "true"
            values["actual_cost_usd"] = values["actual_cost_usd"] or None
            outcomes.append(Outcome.model_validate(values))
        return outcomes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Private folder with session JSON files")
    parser.add_argument("--outcomes", type=Path, help="Optional reconciled CRM/cost CSV")
    parser.add_argument("--output", type=Path, default=Path(".local/evidence-summary.json"))
    args = parser.parse_args()
    try:
        files = sorted(args.directory.glob("*.json"))
        if not files:
            raise ValueError("No session measurement files found")
        records = [SessionEvidence.model_validate_json(path.read_text()) for path in files]
        outcomes = load_outcomes(args.outcomes) if args.outcomes else []
        report = summarize(records, outcomes)
    except (OSError, ValueError, ValidationError, csv.Error, AttributeError, TypeError):
        # Do not print malformed private input or validation errors containing its values.
        parser.exit(2, "Invalid measurement input; check schema, IDs, and CSV columns locally.\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Aggregate report: {args.output}; raw sessions were not copied.")


if __name__ == "__main__":
    main()
