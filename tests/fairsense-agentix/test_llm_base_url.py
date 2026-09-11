"""Tests for ``llm_base_url`` — OpenAI-compatible endpoints (Ollama, vLLM, ...).

The setting must reach every ``ChatOpenAI`` the package constructs; otherwise a
documented local-model setup would silently talk to api.openai.com.
"""

from __future__ import annotations

from typing import Any

import pytest

from fairsense_agentix.configs.settings import Settings


pytestmark = pytest.mark.unit

OLLAMA_URL = "http://localhost:11434/v1"


def _local_settings(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> Settings:
    """Build Settings for an OpenAI-compatible local server (Ollama-style)."""
    monkeypatch.setenv("FAIRSENSE_LLM_PROVIDER", "openai")
    monkeypatch.setenv("FAIRSENSE_LLM_API_KEY", "ollama")  # any non-empty value
    monkeypatch.setenv("FAIRSENSE_LLM_BASE_URL", OLLAMA_URL)
    monkeypatch.setenv("FAIRSENSE_LLM_MODEL_NAME", "llama3")
    for key, value in overrides.items():
        monkeypatch.setenv(f"FAIRSENSE_{key.upper()}", str(value))
    return Settings()


class _RecordingChatOpenAI:
    """Stand-in for ChatOpenAI that records constructor kwargs."""

    calls: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        type(self).calls.append(kwargs)

    # The resolvers chain these; return self so the chain stays inert.
    def with_structured_output(self, *_a: Any, **_k: Any) -> _RecordingChatOpenAI:
        return self

    def with_retry(self, *_a: Any, **_k: Any) -> _RecordingChatOpenAI:
        return self


@pytest.fixture
def recording_chat_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> type[_RecordingChatOpenAI]:
    _RecordingChatOpenAI.calls = []
    monkeypatch.setattr("langchain_openai.ChatOpenAI", _RecordingChatOpenAI)
    return _RecordingChatOpenAI


def test_setting_defaults_to_none() -> None:
    assert Settings().llm_base_url is None


def test_setting_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _local_settings(monkeypatch).llm_base_url == OLLAMA_URL


def test_llm_resolver_passes_base_url(
    monkeypatch: pytest.MonkeyPatch,
    recording_chat_openai: type[_RecordingChatOpenAI],
) -> None:
    from fairsense_agentix.tools.resolvers.llm import _build_openai_tool

    cfg = _local_settings(monkeypatch, llm_cache_enabled=False)
    _build_openai_tool(cfg)

    assert recording_chat_openai.calls, "ChatOpenAI was not constructed"
    assert recording_chat_openai.calls[0]["base_url"] == OLLAMA_URL
    assert recording_chat_openai.calls[0]["model"] == "llama3"


def test_summarizer_resolver_passes_base_url(
    monkeypatch: pytest.MonkeyPatch,
    recording_chat_openai: type[_RecordingChatOpenAI],
) -> None:
    from fairsense_agentix.tools.resolvers.summarizer import _resolve_summarizer_tool

    cfg = _local_settings(monkeypatch)
    _resolve_summarizer_tool(cfg)

    assert recording_chat_openai.calls[0]["base_url"] == OLLAMA_URL


def test_evaluator_passes_base_url(
    monkeypatch: pytest.MonkeyPatch,
    recording_chat_openai: type[_RecordingChatOpenAI],
) -> None:
    from fairsense_agentix.services.evaluator import bias as evaluator_bias

    cfg = _local_settings(monkeypatch)
    # The evaluator imports ChatOpenAI at module level and reads the global
    # settings object; patch both.
    monkeypatch.setattr(evaluator_bias, "ChatOpenAI", recording_chat_openai)
    monkeypatch.setattr(evaluator_bias, "settings", cfg)

    evaluator_bias._build_plain_langchain_model()

    assert recording_chat_openai.calls[0]["base_url"] == OLLAMA_URL


def test_vlm_passes_base_url(
    monkeypatch: pytest.MonkeyPatch,
    recording_chat_openai: type[_RecordingChatOpenAI],
) -> None:
    from fairsense_agentix.tools.vlm.unified_vlm_tool import UnifiedVLMTool

    cfg = _local_settings(monkeypatch)
    UnifiedVLMTool(settings=cfg)

    assert recording_chat_openai.calls[0]["base_url"] == OLLAMA_URL
