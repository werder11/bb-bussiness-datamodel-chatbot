"""Acceptance level — one test per functional requirement (FR1-FR7),
`docs/architecture/README.md#requirements`. Black-box via the same
`api_client` fixture as the System level (tests/conftest.py); deterministic
paths only, no LLM calls, per the CI/CD fast gate (ADR-0019).
"""


class TestFR1AnswersEntityAndAttributeQuestions:
    def test_answers_which_entities_exist_and_their_core_attributes(self, api_client):
        response = api_client.post("/query", json={"question": "What are Account's attributes?"})
        body = response.json()
        assert response.status_code == 200
        assert "accountId" in body["answer"]


class TestFR2AnswersRelationshipQuestionsIncludingMultiHop:
    def test_answers_a_relationship_that_is_not_a_direct_single_hop(self, api_client):
        # Account -> Contact (polymorphic "customer") -> Organization: two hops,
        # not a direct reference — the exact shape ADR-0009 exists for.
        response = api_client.post(
            "/query", json={"question": "How does Account relate to Organization?"}
        )
        body = response.json()
        assert response.status_code == 200
        assert body["route"] == "traversal"
        assert body["grounded"] is True


class TestFR3AnswersAreGroundedOrExplicitlyRefused:
    def test_out_of_scope_question_is_refused_not_guessed(self, api_client):
        response = api_client.post("/query", json={"question": "What is the capital of France?"})
        body = response.json()
        assert response.status_code == 200
        assert body["grounded"] is False
        assert "ingested CDM scope" in body["answer"]


class TestFR4ScopeIsBankingAndCommonEntities:
    def test_ingested_scope_includes_both_banking_and_common_namespaces(self, api_client):
        response = api_client.get("/entities")
        entities = response.json()["entities"]
        assert any(name.startswith("banking:") for name in entities)
        assert any(name.startswith("crmCommon:") for name in entities)


class TestFR5ExposedAsAContainerizedHTTPAPI:
    def test_reachable_over_http(self, api_client):
        # The container half of FR5 (`task docker:build && task docker:run`)
        # is verified manually once the Dockerfile lands (Phase 7) — this
        # test covers the "exposed as an HTTP API" half only.
        health = api_client.get("/health")
        query = api_client.post("/query", json={"question": "What are Account's attributes?"})
        assert health.status_code == 200
        assert query.status_code == 200


class TestFR6IngestionPopulatesTheRetrievalIndexes:
    def test_populated_index_is_reachable_end_to_end(self, api_client):
        # CDM .cdm.json *parsing* correctness is covered by the Resolver's own
        # Component Integration golden tests (tests/integration/test_resolver.py)
        # and by `task ingest:run` against the real corpus. This test covers
        # the other half: an ingested index is actually reachable through the
        # full API stack.
        response = api_client.get("/entities/banking:Account")
        assert response.status_code == 200
        assert response.json()["attributes"]


class TestFR7QualityIsMeasurableNotJustAsserted:
    def test_every_response_carries_explicit_groundedness_and_verification_signals(
        self, api_client
    ):
        # Full KPI reporting (Faithfulness, Recall@K, refusal accuracy, ...)
        # is Phase 8's evaluation dataset/runner. This test covers the
        # prerequisite: every response exposes structured, checkable
        # groundedness fields rather than an opaque answer string.
        grounded = api_client.post(
            "/query", json={"question": "What are Account's attributes?"}
        ).json()
        refused = api_client.post(
            "/query", json={"question": "What is the capital of France?"}
        ).json()

        assert (grounded["grounded"], grounded["verified"]) == (True, True)
        assert (refused["grounded"], refused["verified"]) == (False, False)
