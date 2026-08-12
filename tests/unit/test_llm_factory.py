"""Component/Unit tests for the LLM provider factory — ADR-0024.

Only checks which adapter *class* gets selected. Real construction is
unavoidable here (`build_llm` returns a constructed instance, not a class),
so a dummy `GEMINI_API_KEY` is set where needed — unlike Anthropic's SDK,
`google.genai.Client()` raises immediately with no key at all (validates
*something* is present, not that it works; a real API call would still be
needed to prove the key is valid, and none happens in these tests).
"""

import pytest

from app.adapters.llm_anthropic import AnthropicLLM
from app.adapters.llm_factory import build_llm
from app.adapters.llm_gemini import GeminiLLM


class TestBuildLlm:
    def test_explicit_provider_argument_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
        llm = build_llm(provider="anthropic")
        assert isinstance(llm, AnthropicLLM)

    def test_gemini_provider_selected_explicitly(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
        llm = build_llm(provider="gemini")
        assert isinstance(llm, GeminiLLM)

    def test_provider_selection_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
        llm = build_llm(provider="GEMINI")
        assert isinstance(llm, GeminiLLM)

    def test_env_var_used_when_no_explicit_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
        llm = build_llm()
        assert isinstance(llm, GeminiLLM)

    def test_defaults_to_anthropic_when_unset(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        llm = build_llm()
        assert isinstance(llm, AnthropicLLM)

    def test_unknown_provider_raises_a_clear_error(self):
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            build_llm(provider="openai")
