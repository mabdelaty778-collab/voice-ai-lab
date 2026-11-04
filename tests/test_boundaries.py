import pytest

from tests.test_workflow import sample
from voice_ai_lab.knowledge import answer, search


@pytest.mark.parametrize("path", ["catalog", "leads", "metrics"])
def test_authentication_required(client, path):
    assert client.get("/api/v1/" + path).status_code == 401
    assert client.get("/api/v1/" + path, headers={"X-Lab-Key": "wrong"}).status_code == 401


@pytest.mark.parametrize("path,body", [("questions", {"text": "python"}), ("leads", None)])
def test_writes_require_key(client, path, body):
    assert client.post("/api/v1/" + path, json=body or sample()).status_code == 401


def test_key_in_query_is_not_accepted(client, headers):
    assert client.get("/api/v1/leads?api_key=" + headers["X-Lab-Key"]).status_code == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"consent": False},
        {"consent": 1},
        {"email": "someone@gmail.com"},
        {"course_id": "fake-course"},
        {"request_id": "not-a-uuid"},
        {"name": " "},
        {"unexpected": "field"},
    ],
)
def test_invalid_lead_does_not_persist(client, headers, changes):
    data = sample(**changes)
    response = client.post("/api/v1/leads", headers=headers, json=data)
    assert response.status_code == 422
    assert "someone@gmail.com" not in response.text
    assert client.get("/api/v1/leads", headers=headers).json()["meta"]["total"] == 0


@pytest.mark.parametrize("query", ["xyzzy", "the and a", "", "🛸"])
def test_unknown_search_does_not_return_unrelated_courses(query):
    assert search(query) == []
    assert answer(query)["sources"] == []
    assert "could not find" in answer(query)["reply"]


def test_arabic_keyword_is_supported_without_claiming_translation():
    assert search("بايثون")[0]["id"] == "python-automation"


@pytest.mark.parametrize("text", ["", " ", "x" * 501])
def test_question_size_and_whitespace(client, headers, text):
    assert client.post("/api/v1/questions", headers=headers, json={"text": text}).status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_pagination_bounds(client, headers, query):
    assert client.get("/api/v1/leads?" + query, headers=headers).status_code == 422


def test_host_and_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/health").json()["external_services"] is False


def test_frontend_does_not_store_keys_or_insert_dynamic_html(client):
    script = client.get("/static/app.js").text
    assert "localStorage" not in script
    assert "innerHTML" not in script
    assert "textContent" in script
