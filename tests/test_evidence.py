"""Measurement checks focus on misleading statistics, missing data, and privacy."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from scripts.benchmark_local import run_benchmark
from voice_ai_lab.evidence import (
    AssistantMeasurement,
    Outcome,
    SessionEvidence,
    distribution,
    load_outcomes,
    summarize,
    write_session,
)


def test_percentiles_have_stated_nearest_rank_and_empty_samples():
    result = distribution([5, 5, 5, 400])
    assert result == {"n": 4, "p50_ms": 5, "p90_ms": 400, "p95_ms": 400}
    assert distribution([]) == {"n": 0, "p50_ms": None, "p90_ms": None, "p95_ms": None}


def test_unknown_outcomes_costs_and_latency_are_not_zero():
    record = SessionEvidence(duration_seconds=90)
    group = summarize([record])["groups"][0]
    assert group["sdk_response_latency"]["n"] == 0
    assert group["crm_converted"]["rate"] is None
    assert group["terminal_errors"]["rate"] is None
    assert group["cost"]["known_total_usd"] is None
    assert group["cost"]["coverage"] == 0


def test_partial_cost_denominator_and_interrupted_messages():
    first = SessionEvidence(
        duration_seconds=90,
        assistant_messages=[
            AssistantMeasurement(sdk_e2e_ms=1000),
            AssistantMeasurement(sdk_e2e_ms=9000, interrupted=True),
            AssistantMeasurement(),
        ],
    )
    second = SessionEvidence(duration_seconds=120)
    outcome = Outcome(session_id=first.session_id, qualified=True, actual_cost_usd=0.2)
    group = summarize([first, second], [outcome])["groups"][0]
    assert group["sdk_response_latency"]["p90_ms"] == 1000
    assert group["interrupted_messages_excluded"] == 1
    assert group["messages_without_latency"] == 1
    assert group["cost"]["coverage"] == 0.5
    assert group["cost"]["mean_per_costed_session_usd"] == 0.2
    assert group["crm_qualified"] == {"observed": 1, "positive": 1, "rate": 1}
    assert group["crm_converted"]["observed"] == 0
    assert str(first.session_id) not in json.dumps(summarize([first, second], [outcome]))


def test_environments_and_language_routes_are_not_pooled():
    records = [
        SessionEvidence(duration_seconds=1, environment="lab"),
        SessionEvidence(duration_seconds=1, environment="production"),
        SessionEvidence(duration_seconds=1, route="pipeline", language="ar"),
    ]
    assert len(summarize(records)["groups"]) == 3


def test_duplicate_or_unmatched_records_fail_instead_of_double_counting():
    record = SessionEvidence(duration_seconds=10)
    outcome = Outcome(session_id=record.session_id, converted=True)
    with pytest.raises(ValueError, match="Duplicate session"):
        summarize([record, record])
    with pytest.raises(ValueError, match="Duplicate outcome"):
        summarize([record], [outcome, outcome])
    with pytest.raises(ValueError, match="no matching"):
        summarize([record], [Outcome(session_id=uuid4())])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1])
def test_nonfinite_or_negative_measurements_are_rejected(bad):
    with pytest.raises(ValidationError):
        AssistantMeasurement(sdk_e2e_ms=bad)
    with pytest.raises(ValidationError):
        Outcome(session_id=uuid4(), actual_cost_usd=bad)


def test_unexpected_fields_cannot_smuggle_contact_data():
    with pytest.raises(ValidationError):
        SessionEvidence(duration_seconds=1, phone="private-value")


def test_csv_preserves_missing_values_and_requires_explicit_booleans(tmp_path):
    path = tmp_path / "outcomes.csv"
    prefix = "session_id,qualified,converted,actual_cost_usd\n"
    path.write_text(prefix + f"{uuid4()},true,,0\n")
    outcome = load_outcomes(path)[0]
    assert outcome.qualified is True
    assert outcome.converted is None
    assert outcome.actual_cost_usd == 0
    path.write_text(prefix + f"{uuid4()},yes,,\n")
    with pytest.raises(ValueError, match="flags"):
        load_outcomes(path)


def test_exports_refuse_to_overwrite_session_receipts(tmp_path):
    record = SessionEvidence(duration_seconds=1)
    target = write_session(tmp_path, record)
    assert SessionEvidence.model_validate_json(target.read_text()) == record
    with pytest.raises(FileExistsError):
        write_session(tmp_path, record)


def test_local_benchmark_uses_no_external_sockets_and_checks_durable_results():
    report = run_benchmark(samples=2, workers=2)
    assert report["checks"]["sequential_expected_results"] == 6
    assert report["checks"]["concurrent_retries_one_committed_record"] == 8
    assert report["checks"]["injected_failure_no_false_success"]
    assert report["checks"]["restart_durability_and_recovery"]
    assert report["sequential_latency"]["committed_save"]["n"] == 2
    assert report["provider_calls"] == 0
