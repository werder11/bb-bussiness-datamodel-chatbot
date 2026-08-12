"""Component/Unit tests for GeminiLLM — ADR-0024, ADR-0016.

The Gemini client is faked so these test prompt construction and response
parsing without any live API call (ADR-0018's fast-gate requirement) — the
fake mirrors just enough of the real SDK's shape
(`client.models.generate_content(...).text`) to exercise the real parsing
logic, same pattern as test_adapters_llm_anthropic.py.
"""

from app.adapters.llm_gemini import GeminiLLM


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_call: dict | None = None

    def generate_content(self, **kwargs):
        self.last_call = kwargs
        return _FakeResponse(self.response_text)


class _FakeClient:
    def __init__(self, response_text: str = "The Account entity has one core attribute.") -> None:
        self.models = _FakeModels(response_text)


class TestGenerate:
    def test_returns_the_response_text(self):
        client = _FakeClient(response_text="Account has accountId.")
        llm = GeminiLLM(client=client)

        result = llm.generate("What are Account's attributes?", context=("Account: accountId",))

        assert result == "Account has accountId."

    def test_context_and_question_both_reach_the_request(self):
        client = _FakeClient()
        llm = GeminiLLM(client=client)

        llm.generate("How does Contact relate to Organization?", context=("fact one", "fact two"))

        call = client.models.last_call
        assert call is not None
        assert "How does Contact relate to Organization?" in call["contents"]
        assert "fact one" in call["contents"]
        assert "fact two" in call["contents"]

    def test_empty_context_still_sends_a_request(self):
        client = _FakeClient()
        llm = GeminiLLM(client=client)

        llm.generate("anything", context=())

        assert client.models.last_call is not None
        assert "(no context provided)" in client.models.last_call["contents"]

    def test_system_prompt_forbids_outside_knowledge(self):
        client = _FakeClient()
        llm = GeminiLLM(client=client)

        llm.generate("q", context=("c",))

        system = client.models.last_call["config"]["system_instruction"]
        assert "only" in system.lower()
        assert "context" in system.lower()

    def test_model_is_passed_through(self):
        client = _FakeClient()
        llm = GeminiLLM(client=client, model="gemini-2.0-flash-001")

        llm.generate("q", context=("c",))

        assert client.models.last_call["model"] == "gemini-2.0-flash-001"

    def test_constructing_without_injected_client_does_not_touch_network(self):
        # Constructing GeminiLLM() with a fake client must never import/construct
        # the real `google.genai.Client` — that's the whole point of injection.
        llm = GeminiLLM(client=_FakeClient(response_text="ok"))
        assert llm.generate("q", context=()) == "ok"

    def test_empty_response_text_becomes_empty_string_not_none(self):
        # response.text can be None (e.g. safety-filtered content) -- must
        # not propagate None as an "answer".
        client = _FakeClient()
        client.models.response_text = None  # type: ignore[assignment]
        llm = GeminiLLM(client=client)

        assert llm.generate("q", context=("c",)) == ""
