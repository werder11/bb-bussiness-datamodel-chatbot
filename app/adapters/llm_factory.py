"""LLM provider selection — ADR-0024.

A single, tiny factory so `app/api/main.py` and `tests/eval/run.py` don't
duplicate provider-selection logic. Not a plugin registry — only two
providers exist, and ADR-0001's port/adapter boundary is what makes adding
a third trivial without touching this file's callers, not extra machinery
here.
"""

import os
from collections.abc import Callable

from app.adapters.llm_anthropic import AnthropicLLM
from app.adapters.llm_gemini import GeminiLLM
from app.domain.ports import LLM

_PROVIDERS: dict[str, Callable[[], LLM]] = {
    "anthropic": AnthropicLLM,
    "gemini": GeminiLLM,
}


def build_llm(provider: str | None = None) -> LLM:
    """`provider` defaults to the `LLM_PROVIDER` env var, then "anthropic"
    (ADR-0023's original choice) if unset."""
    name = (provider or os.environ.get("LLM_PROVIDER", "anthropic")).lower()
    try:
        adapter_cls = _PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown LLM_PROVIDER '{name}' — choose one of {sorted(_PROVIDERS)}") from None
    return adapter_cls()
