"""Component/Unit tests for the Retrieval Tracer shape — `docs/operations/monitoring.md`."""

import pytest
from pydantic import ValidationError

from app.domain.tracing import build_trace


class TestBuildTrace:
    def test_holds_exactly_the_documented_fields(self):
        trace = build_trace(
            query="What are Account's attributes?",
            matched_entities=("banking:Account",),
            route="structured",
            grounded=True,
            verified=True,
        )
        assert trace.query == "What are Account's attributes?"
        assert trace.matched_entities == ("banking:Account",)
        assert trace.route == "structured"
        assert trace.grounded is True
        assert trace.verified is True
        assert trace.error is None

    def test_error_field_defaults_to_none_and_can_be_set(self):
        trace = build_trace(
            query="q", matched_entities=(), route="semantic", grounded=True, verified=False
        )
        assert trace.error is None

        trace_with_error = build_trace(
            query="q",
            matched_entities=(),
            route="semantic",
            grounded=True,
            verified=False,
            error="429 RESOURCE_EXHAUSTED",
        )
        assert trace_with_error.error == "429 RESOURCE_EXHAUSTED"

    def test_is_frozen(self):
        trace = build_trace(
            query="q", matched_entities=(), route="none", grounded=False, verified=False
        )
        with pytest.raises(ValidationError):
            trace.grounded = True  # type: ignore[misc]

    def test_invalid_route_rejected(self):
        with pytest.raises(ValidationError):
            build_trace(
                query="q",
                matched_entities=(),
                route="bogus",  # type: ignore[arg-type]
                grounded=False,
                verified=False,
            )
