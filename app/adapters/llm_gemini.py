"""Google Gemini adapter for the `LLM` port — ADR-0024 (second LLM provider,
free-tier via Google AI Studio; also a concrete demonstration that ADR-0001's
port/adapter boundary makes swapping providers a new adapter, not a domain
change).

Mirrors app/adapters/llm_anthropic.py's structure and dependency-injection
pattern exactly: the underlying client is injectable so unit tests exercise
real prompt-construction/response-parsing logic against a fake client,
never a live API call (ADR-0018's fast-gate requirement). `generate()`
itself imports nothing from `google.genai` — the config it sends is a plain
dict (the SDK accepts either a dict or its typed `GenerateContentConfig`) —
so, like the Anthropic adapter, only `_build_client` ever touches the real
SDK, and unit tests need nothing beyond a hand-rolled fake.
"""

from typing import Any, Protocol

_MODEL = "gemini-flash-latest"  # small/fast, free-tier eligible via Google AI Studio
_SYSTEM_PROMPT = (
    "You are answering questions about the Microsoft Common Data Model (CDM) "
    "using only the context provided below. Never use outside knowledge. If "
    "the context does not contain enough information to answer, say so "
    "plainly instead of guessing."
)


class _GeminiClientLike(Protocol):
    @property
    def models(self) -> Any: ...


class GeminiLLM:
    """Implements the `LLM` Protocol (app/domain/ports.py)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _MODEL,
        client: _GeminiClientLike | None = None,
    ) -> None:
        self._model = model
        self._client = client or self._build_client(api_key)

    @staticmethod
    def _build_client(api_key: str | None) -> _GeminiClientLike:
        # Deferred import: no cost/construction when a fake client is injected (tests).
        from google import genai

        # api_key=None makes the real SDK read GEMINI_API_KEY/GOOGLE_API_KEY
        # from the environment itself, same pattern as AnthropicLLM.
        return genai.Client(api_key=api_key) if api_key else genai.Client()

    def generate(self, question: str, context: tuple[str, ...]) -> str:
        context_block = "\n\n".join(context) if context else "(no context provided)"
        response = self._client.models.generate_content(
            model=self._model,
            contents=f"Context:\n{context_block}\n\nQuestion: {question}",
            config={"system_instruction": _SYSTEM_PROMPT},
        )
        return response.text or ""
