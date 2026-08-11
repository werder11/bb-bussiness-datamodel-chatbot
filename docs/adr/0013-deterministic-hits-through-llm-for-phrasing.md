# ADR-0013: Deterministic Structured Hits Still Go Through the LLM for Phrasing

**Status:** Superseded by [ADR-0016](0016-deterministic-hits-template-rendered.md)
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

For a fully-deterministic structured hit (e.g. "what are Account's attributes"), the retrieved facts already contain the complete answer — generation is arguably just phrasing, not reasoning.

## Decision (original, no longer in effect)

Route structured hits through the same Answer Generator as everything else, rather than a separate template-only path, to keep one code path and one place the verification step needs to check. Natural-language phrasing is also simply a better demo experience than a raw fact dump.

## Consequences (as originally assessed)

### Positive
- One generation path to build, test, and verify instead of two; consistent voice across all answer types.

### Negative
- Adds LLM cost/latency to questions that didn't strictly need it, and a small residual risk that phrasing introduces a subtle inaccuracy even from correct source facts.

## Why Superseded

On reconsideration, a template rendered directly from verified structured facts has **zero hallucination surface** for that question class — there's nothing left to fabricate. Given non-hallucination is explicitly graded, and given the architectural principle this demonstrates (use the LLM where semantic interpretation adds value, not for operations a database can already answer deterministically), the cost/latency/risk savings outweigh the "one code path" simplicity this ADR originally optimized for. See [ADR-0016](0016-deterministic-hits-template-rendered.md).

## Related Decisions

- [ADR-0016](0016-deterministic-hits-template-rendered.md) — supersedes this decision
