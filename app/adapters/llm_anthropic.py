"""Anthropic Claude adapter for the `LLM` port — ADR-0023, ADR-0016
(context-only generation; never called for fully-deterministic hits).

The system prompt's "answer only from context" instruction is defense in
depth, not the real enforcement — the Grounding Guard (ADR-0005) and
Grounding Validator (ADR-0010) are what actually prevent hallucination.

The underlying client is dependency-injected so unit tests exercise the
real prompt-construction/response-parsing logic against a fake client,
never a live API call (ADR-0018's fast-gate requirement).
"""

from typing import Any, Protocol

_MODEL = "claude-haiku-4-5-20251001"  # small/fast/cheap — latency isn't critical, cost should stay low
_MAX_TOKENS = 512
_SYSTEM_PROMPT = (
    "You are answering questions about the Microsoft Common Data Model (CDM) "
    "using only the context provided below. Never use outside knowledge. If "
    "the context does not contain enough information to answer, say so "
    "plainly instead of guessing."
)


class _AnthropicClientLike(Protocol):
    @property
    def messages(self) -> Any: ...


class AnthropicLLM:
    """Implements the `LLM` Protocol (app/domain/ports.py)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _MODEL,
        client: _AnthropicClientLike | None = None,
    ) -> None:
        self._model = model
        self._client = client or self._build_client(api_key)

    @staticmethod
    def _build_client(api_key: str | None) -> _AnthropicClientLike:
        # Deferred import: no cost/construction when a fake client is injected (tests).
        from anthropic import Anthropic

        return Anthropic(api_key=api_key)

    def generate(self, question: str, context: tuple[str, ...]) -> str:
        context_block = "\n\n".join(context) if context else "(no context provided)"
        response = self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {question}"}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))
