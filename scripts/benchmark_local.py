"""Measure the local ASGI/SQLite lab, without network or voice-provider calls.

This measures in-process HTTP handling via TestClient, not audible response latency.
Usage: python scripts/benchmark_local.py --samples 100 --workers 8
"""

import argparse
import json
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from voice_ai_lab.api import create_app
from voice_ai_lab.config import Settings
from voice_ai_lab.evidence import distribution


def run_benchmark(samples: int = 100, workers: int = 8) -> dict:
    if not 1 <= samples <= 10_000 or not 1 <= workers <= 32:
        raise ValueError("Use 1–10000 samples and 1–32 workers")
    headers = {"X-Lab-Key": "local-benchmark-only-no-external-credentials"}
    latencies = {"lookup": [], "committed_save": [], "idempotent_replay": []}
    checks = {}

    def lead():
        return {
            "name": "Benchmark Learner",
            "email": "benchmark@example.com",
            "course_id": "voice-agents",
            "consent": True,
            "request_id": str(uuid4()),
        }

    with TemporaryDirectory(prefix="voice-lab-benchmark-") as directory:
        settings = Settings(api_key=headers["X-Lab-Key"], db_path=Path(directory) / "lab.sqlite3")
        app = create_app(settings)
        with TestClient(app) as client:
            # Excluded warmups; first-use import and startup time are not measured.
            for _ in range(10):
                assert (
                    client.post(
                        "/api/v1/questions", headers=headers, json={"text": "voice agents"}
                    ).status_code
                    == 200
                )
            for _ in range(samples):
                payload = lead()
                cases = (
                    ("lookup", "/api/v1/questions", {"text": "voice agents"}, 200),
                    ("committed_save", "/api/v1/leads", payload, 201),
                    ("idempotent_replay", "/api/v1/leads", payload, 200),
                )
                saved_id = None
                for name, path, body, expected in cases:
                    started = time.perf_counter()
                    response = client.post(path, headers=headers, json=body)
                    latencies[name].append((time.perf_counter() - started) * 1000)
                    assert response.status_code == expected
                    result = response.json()
                    if name == "lookup":
                        assert "voice-agents" in result["data"]["sources"]
                    else:
                        assert result["persisted"] is True
                        if name == "committed_save":
                            saved_id = result["data"]["id"]
                        else:
                            assert result["replayed"] and result["data"]["id"] == saved_id
            checks["sequential_expected_results"] = samples * 3
            payload = lead()

            def retry(_):
                return client.post("/api/v1/leads", headers=headers, json=payload)

            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=workers) as pool:
                replies = list(pool.map(retry, range(workers * 4)))
            concurrency_ms = (time.perf_counter() - started) * 1000
            assert sum(r.status_code == 201 for r in replies) == 1
            assert all(r.status_code in (200, 201) for r in replies)
            assert len({r.json()["data"]["id"] for r in replies}) == 1
            checks["concurrent_retries_one_committed_record"] = len(replies)
            app.state.store.fail_writes = True
            failed_payload = lead()
            failure = client.post("/api/v1/leads", headers=headers, json=failed_payload)
            assert failure.status_code == 503 and "persisted" not in failure.json()
            assert app.state.store.leads(1, 0)[1] == samples + 1
            checks["injected_failure_no_false_success"] = True

        # New app and connections over the same temporary file verify restart durability.
        with TestClient(create_app(settings)) as restarted:
            rows = restarted.get("/api/v1/leads", headers=headers)
            assert rows.json()["meta"]["total"] == samples + 1
            recovered = restarted.post("/api/v1/leads", headers=headers, json=failed_payload)
            assert recovered.status_code == 201 and recovered.json()["persisted"] is True
            checks["restart_durability_and_recovery"] = True

    return {
        "scope": "local in-process ASGI/SQLite benchmark; no audio or production traffic",
        "recorded_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "warmup_lookup_requests_excluded": 10,
        "sequential_latency": {name: distribution(values) for name, values in latencies.items()},
        "concurrency": {
            "workers": workers,
            "same_request_retries": workers * 4,
            "batch_elapsed_ms": round(concurrency_ms, 3),
        },
        "checks": checks,
        "provider_calls": 0,
        "provider_usage_cost_usd": 0,
        "host_cost_usd": None,
        "temporary_database_removed": True,
        "result": "passed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path(".local/local-benchmark.json"))
    args = parser.parse_args()
    report = run_benchmark(args.samples, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
