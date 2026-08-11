# Quality

Not part of the base skill template's seven layers — added because this project treats quality assurance as two distinct, first-class disciplines rather than folding it into Architecture or ADRs alone ([ADR-0017](../adr/0017-evaluation-as-first-class-layer.md), [ADR-0018](../adr/0018-testing-strategy-istqb-aligned.md)):

- [Testing Strategy](testing-strategy.md) — does the code do what it was coded to do? Deterministic, pass/fail, ISTQB-aligned levels.
- [Evaluation Strategy](evaluation-strategy.md) — is the system's *output* actually good? Empirical, measured, named industry metrics (RAGAS, ISTQB CT-AI).

These are deliberately different disciplines with different tooling and different places in [Operations: CI/CD](../operations/ci-cd.md) — see each page's own rationale for why conflating them would be a mistake.
