import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voice_ai_lab.api import create_app
from voice_ai_lab.config import Settings

KEY = "unit-test-key-only-not-a-real-secret"


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not call external services")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


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
