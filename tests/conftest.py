import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voice_ai_lab.api import create_app
from voice_ai_lab.config import Settings

KEY = "unit-test-key-only-not-a-real-secret"


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def guarded_connect(sock, address):
        # Windows implements asyncio's socketpair with a loopback TCP connection.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        raise AssertionError("Tests must not call external services")

    def guarded_connect_ex(sock, address):
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect_ex(sock, address)
        raise AssertionError("Tests must not call external services")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture
def settings(tmp_path: Path):
    return Settings(api_key=KEY, db_path=tmp_path / "lab.sqlite3")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def headers():
    return {"X-Lab-Key": KEY}
