"""Integration tests for the FastAPI /ask endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Return a FastAPI TestClient with the orchestrator mocked out."""
    with patch("src.web_app.server.process_query") as mock_process:
        mock_process.return_value = {
            "answer": "Diversification means spreading investments across asset classes.",
            "agent": "finance_qa_agent",
            "session_id": "test-session-123",
        }
        from src.web_app.server import app
        yield TestClient(app)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAskEndpoint:
    def test_ask_returns_200_with_answer(self, client):
        response = client.post("/ask", json={"question": "What is diversification?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_ask_response_contains_agent_field(self, client):
        response = client.post("/ask", json={"question": "What is a bond?"})
        assert response.status_code == 200
        data = response.json()
        assert "agent" in data

    def test_ask_echoes_question(self, client):
        question = "What is a mutual fund?"
        response = client.post("/ask", json={"question": question})
        assert response.status_code == 200
        assert response.json()["question"] == question

    def test_ask_empty_question_returns_422(self, client):
        response = client.post("/ask", json={"question": ""})
        assert response.status_code == 422

    def test_ask_missing_body_returns_422(self, client):
        response = client.post("/ask", json={})
        assert response.status_code == 422
