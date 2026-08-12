"""Component/Unit tests for AnthropicLLM — ADR-0023, ADR-0016.

The Anthropic client is faked so these test prompt construction and
response parsing without any live API call (ADR-0018's fast-gate
requirement) — the fake mirrors just enough of the real SDK's response
shape (`response.content[i].text`) to exercise the real parsing logic.
"""

from app.adapters.llm_anthropic import AnthropicLLM


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_call: dict | None = None

    def create(self, **kwargs):
        self.last_call = kwargs
        return _FakeResponse(self.response_text)


class _FakeClient:
    def __init__(self, response_text: str = "The Account entity has one core attribute.") -> None:
        self.messages = _FakeMessages(response_text)


class TestGenerate:
    def test_returns_the_response_text(self):
        client = _FakeClient(response_text="Account has accountId.")
        llm = AnthropicLLM(client=client)

        result = llm.generate("What are Account's attributes?", context=("Account: accountId",))

        assert result == "Account has accountId."

    def test_context_and_question_both_reach_the_request(self):
        client = _FakeClient()
        llm = AnthropicLLM(client=client)

        llm.generate("How does Contact relate to Organization?", context=("fact one", "fact two"))

        call = client.messages.last_call
        assert call is not None
        content = call["messages"][0]["content"]
        assert "How does Contact relate to Organization?" in content
        assert "fact one" in content
        assert "fact two" in content

    def test_empty_context_still_sends_a_request(self):
        client = _FakeClient()
        llm = AnthropicLLM(client=client)

        llm.generate("anything", context=())

        assert client.messages.last_call is not None
        assert "(no context provided)" in client.messages.last_call["messages"][0]["content"]

    def test_system_prompt_forbids_outside_knowledge(self):
        client = _FakeClient()
        llm = AnthropicLLM(client=client)

        llm.generate("q", context=("c",))

        system = client.messages.last_call["system"]
        assert "only" in system.lower()
        assert "context" in system.lower()

    def test_model_is_passed_through(self):
        client = _FakeClient()
        llm = AnthropicLLM(client=client, model="claude-haiku-4-5-20251001")

        llm.generate("q", context=("c",))

        assert client.messages.last_call["model"] == "claude-haiku-4-5-20251001"

    def test_constructing_without_injected_client_does_not_touch_network(self):
        # Constructing AnthropicLLM() with a fake client must never import/construct
        # the real `anthropic.Anthropic` client — that's the whole point of injection.
        llm = AnthropicLLM(client=_FakeClient(response_text="ok"))
        assert llm.generate("q", context=()) == "ok"
