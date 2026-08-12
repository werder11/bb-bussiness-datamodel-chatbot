"""System level — full FastAPI app, real (small, fixture) corpus, black-box
via TestClient. Deterministic (template-rendered) paths only — no LLM calls,
per the CI/CD fast gate (ADR-0019). `api_client` is defined in
tests/conftest.py.
"""


class TestHealth:
    def test_returns_ok(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCacheControl:
    """Regression: index.html was served with no Cache-Control header at
    all, so a browser could silently keep showing a stale UI build after a
    real rebuild — found live, not by reading the code."""

    def test_non_asset_responses_always_revalidate(self, api_client):
        response = api_client.get("/health")
        assert response.headers["cache-control"] == "no-cache"

    def test_hashed_assets_are_cached_immutably(self, api_client):
        response = api_client.get("/assets/whatever-hashed-name.js")
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


class TestListEntities:
    def test_returns_all_loaded_entities(self, api_client):
        response = api_client.get("/entities")
        assert response.status_code == 200
        assert set(response.json()["entities"]) == {
            "banking:Account",
            "crmCommon:Contact",
            "crmCommon:Organization",
        }


class TestGetEntity:
    def test_known_entity_returns_full_detail(self, api_client):
        response = api_client.get("/entities/banking:Account")
        assert response.status_code == 200
        body = response.json()
        assert body["entity"] == "banking:Account"
        assert any(a["name"] == "accountId" for a in body["attributes"])
        assert any(r["name"] == "customer" for r in body["relationships"])

    def test_unknown_entity_returns_404(self, api_client):
        response = api_client.get("/entities/banking:DoesNotExist")
        assert response.status_code == 404


class TestQueryDeterministicRoutes:
    def test_attribute_question_is_template_rendered(self, api_client):
        response = api_client.post("/query", json={"question": "What are Account's attributes?"})
        assert response.status_code == 200
        body = response.json()
        assert body["route"] == "structured"
        assert body["grounded"] is True
        assert body["verified"] is True
        assert "accountId" in body["answer"]

    def test_single_hop_relationship_question(self, api_client):
        response = api_client.post(
            "/query", json={"question": "What is Contact connected to?"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["route"] == "structured"
        assert "organization" in body["answer"]

    def test_two_hop_traversal_question(self, api_client):
        response = api_client.post(
            "/query", json={"question": "How does Account relate to Organization?"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["route"] == "traversal"
        assert body["grounded"] is True
        assert "banking:Account" in body["answer"]
        assert "crmCommon:Organization" in body["answer"]

    def test_off_scope_question_is_refused_without_llm(self, api_client):
        response = api_client.post(
            "/query", json={"question": "What is the capital of France?"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["route"] == "none"
        assert body["grounded"] is False
        assert "ingested CDM scope" in body["answer"]


class TestEvaluate:
    """POST /evaluate — runs the real pipeline (deterministic route here, no
    LLM call, per ADR-0019) and compares the real answer to a user-supplied
    desired answer via app/domain/comparison.py."""

    def test_close_desired_answer_scores_high_overlap(self, api_client):
        response = api_client.post(
            "/evaluate",
            json={
                "question": "What are Account's attributes?",
                "expected_answer": "Account should have an accountId field.",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query"]["route"] == "structured"
        assert body["query"]["grounded"] is True
        comparison = body["comparison"]
        assert 0.0 <= comparison["similarity"] <= 1.0
        assert "accountid" in comparison["shared_terms"]
        assert "account" in comparison["shared_terms"]

    def test_unrelated_desired_answer_scores_low_overlap(self, api_client):
        response = api_client.post(
            "/evaluate",
            json={
                "question": "What are Account's attributes?",
                "expected_answer": "This describes a completely different topic entirely.",
            },
        )
        assert response.status_code == 200
        comparison = response.json()["comparison"]
        assert comparison["shared_terms"] == []
        assert "topic" in comparison["missing_terms"]

    def test_empty_expected_answer_yields_no_missing_terms(self, api_client):
        response = api_client.post(
            "/evaluate",
            json={"question": "What are Account's attributes?", "expected_answer": ""},
        )
        assert response.status_code == 200
        assert response.json()["comparison"]["missing_terms"] == []
