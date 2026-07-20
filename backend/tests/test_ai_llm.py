"""AI draft LLM provider selection (OpenAI, Ollama, heuristic)."""

import json
from io import BytesIO
from unittest import mock

import pytest

from projects.ai import _call_ai_json, draft_project_content
from projects.models import Project


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="AI Test Project",
        manager=user,
    )


@pytest.mark.django_db
def test_draft_prefers_openai_over_ollama(project, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    openai_content = json.dumps(
        {
            "risks": [
                {
                    "title": "LLM risk",
                    "description": "From OpenAI",
                    "probability": 3,
                    "impact": 3,
                    "mitigation": "Mitigate",
                    "status": "open",
                }
            ]
        }
    )

    def fake_urlopen(request, timeout=30):
        url = request.full_url
        if "openai.com" in url:
            return mock.Mock(
                read=lambda: json.dumps(
                    {"choices": [{"message": {"content": openai_content}}]}
                ).encode(),
                __enter__=lambda self: self,
                __exit__=mock.Mock(return_value=False),
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("projects.ai.urllib.request.urlopen", fake_urlopen)
    result = draft_project_content(project, target="risks")
    assert result["source"] == "openai"
    assert result["risks"][0]["title"] == "LLM risk"


@pytest.mark.django_db
def test_draft_uses_ollama_when_openai_missing(project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

    ollama_body = json.dumps(
        {
            "message": {
                "content": json.dumps(
                    {
                        "risks": [
                            {
                                "title": "Ollama risk",
                                "description": "Local LLM",
                                "probability": 2,
                                "impact": 4,
                                "mitigation": "Plan B",
                                "status": "open",
                            }
                        ]
                    }
                )
            }
        }
    ).encode()

    def fake_urlopen(request, timeout=30):
        url = request.full_url
        if url.endswith("/api/chat"):
            return mock.Mock(
                read=lambda: ollama_body,
                __enter__=lambda self: self,
                __exit__=mock.Mock(return_value=False),
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("projects.ai.urllib.request.urlopen", fake_urlopen)
    result = draft_project_content(project, target="risks")
    assert result["source"] == "ollama"
    assert result["risks"][0]["title"] == "Ollama risk"


def test_call_ai_json_returns_none_without_providers(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    data, source = _call_ai_json("system", "user")
    assert data is None
    assert source is None
