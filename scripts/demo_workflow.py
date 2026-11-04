"""Run a real local HTTP walkthrough with fictional data and no provider keys.

Usage: python scripts/demo_workflow.py --output .local/demo-report.json
The server runs in a temporary working directory with an isolated SQLite file.
"""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4


def run_demo() -> dict:
    events = []
    key = secrets.token_urlsafe(32)
    opener = build_opener(ProxyHandler({}))

    def request(port: int, path: str, payload: dict | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request(
            f"http://127.0.0.1:{port}{path}",
            data=body,
            headers={"X-Lab-Key": key, "Content-Type": "application/json"},
            method="POST" if body is not None else "GET",
        )
        try:
            with opener.open(req, timeout=5) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    with TemporaryDirectory(prefix="voice-ai-lab-demo-") as directory:
        root = Path(directory)

        @contextmanager
        def server(fail_writes: bool = False):
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            env = os.environ.copy()
            env.update(
                {
                    "LAB_API_KEY": key,
                    "LAB_DB_PATH": str(root / "demo.sqlite3"),
                    "LAB_FAIL_WRITES": str(fail_writes).lower(),
                    "LAB_ENABLE_VOICE": "false",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            # This exercise never needs provider credentials, even if the caller has them.
            for variable in ["OPENAI_API_KEY", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]:
                env.pop(variable, None)
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "voice_ai_lab.api:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                env=env,
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Lab server exited during startup")
                    try:
                        status, _ = request(port, "/health")
                        if status == 200:
                            break
                    except (URLError, OSError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Lab server did not become ready")
                yield port
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

        def capture(name, port, path, payload=None):
            status, response = request(port, path, payload)
            events.append(
                {
                    "name": name,
                    "request": path,
                    "input": payload,
                    "http_status": status,
                    "response": response,
                }
            )
            return status, response

        lead = {
            "name": "Demo Learner",
            "email": "learner@example.com",
            "course_id": "voice-agents",
            "consent": True,
            "request_id": str(uuid4()),
        }
        recovered_lead = {**lead, "email": "recovery@example.com", "request_id": str(uuid4())}
        with server() as port:
            status, health = capture("Isolated simulation", port, "/health")
            assert status == 200 and health["external_services"] is False
            status, result = capture(
                "Grounded course answer", port, "/api/v1/questions", {"text": "voice agents"}
            )
            assert status == 200 and "voice-agents" in result["data"]["sources"]
            status, result = capture(
                "Honest no-match", port, "/api/v1/questions", {"text": "xyzzy"}
            )
            assert status == 200 and result["data"]["sources"] == []
            status, created = capture("Committed lead", port, "/api/v1/leads", lead)
            assert status == 201 and created["persisted"] is True
            status, replay = capture("Safe retry", port, "/api/v1/leads", lead)
            assert status == 200 and replay["data"]["id"] == created["data"]["id"]
            assert replay["replayed"] is True

        with server(fail_writes=True) as port:
            status, failure = capture(
                "Simulated write failure", port, "/api/v1/leads", recovered_lead
            )
            assert status == 503 and "persisted" not in failure
            status, rows = capture("No false success", port, "/api/v1/leads")
            assert status == 200 and rows["meta"]["total"] == 1

        with server() as port:
            status, recovery = capture("Recovered write", port, "/api/v1/leads", recovered_lead)
            assert status == 201 and recovery["persisted"] is True
            status, replay = capture("Recovered retry", port, "/api/v1/leads", recovered_lead)
            assert status == 200 and replay["replayed"] is True
            status, metrics = capture("Verified final state", port, "/api/v1/metrics")
            assert status == 200 and metrics["data"]["persisted_test_leads"] == 2

    return {
        "mode": "simulation",
        "transport": "real local HTTP",
        "external_provider_calls": 0,
        "temporary_database_removed": True,
        "events": events,
        "result": "passed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".local/demo-report.json"))
    args = parser.parse_args()
    report = run_demo()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for event in report["events"]:
        print(f"PASS  HTTP {event['http_status']}  {event['name']}")
    print("Passed: isolated storage, actual HTTP responses, zero provider calls.")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
