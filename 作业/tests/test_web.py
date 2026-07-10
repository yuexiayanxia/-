import pytest
from fastapi.testclient import TestClient
from codereflex.web.app import create_app
from codereflex.config import Config


class StubAgentLoop:
    async def run(self, task: str):
        from codereflex.models import Session
        return Session(id="test", task=task)


def test_index_page():
    app = create_app(StubAgentLoop(), Config())
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CodeReflex" in resp.text


def test_submit_endpoint():
    app = create_app(StubAgentLoop(), Config())
    client = TestClient(app)
    resp = client.post("/submit", json={"task": "fix test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
