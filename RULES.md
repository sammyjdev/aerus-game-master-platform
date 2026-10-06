# RULES

## Enforced Invariants

This file adapts FORGE to existing repository policy; canonical documents remain authoritative.

- Follow [engineering constraints](docs/PROJECT_CONTEXT_rules_roadmap.md) and the [architecture](docs/PROJECT_CONTEXT_architecture_ard.md): preserve module boundaries, atomic SQLite writes and the single-instance SQLite/WAL deployment constraint. Scaling requires a separate persistence decision.
- Select canonical sources with the [source-of-truth matrix](docs/ai-ops/source-of-truth-matrix.md), then use the relevant existing [playbook](docs/ai-ops/agents/README.md) and [skill card](docs/ai-ops/skills/skill-cards.md). Do not introduce a parallel workflow.
- Observe a focused failing regression before implementation. Preserve migration data and historical records, campaign isolation, auth/secrets, WS parity, canonical lore and provider-routing contracts when affected.
- Run the complete configured gate and the applicable [harness gates](docs/ai-ops/harness/gates-matrix.md). Apply the existing [regression policy](docs/ai-ops/harness/regression-policy.md); skipped or blocked checks are not passes. Do not reduce the gate to manufacture a green baseline.
- Record revision, environment, exact commands, exit status, failures and evidence in the [validation log](docs/ai-ops/evidence/agent-validation-log.md). Use disposable test credentials and storage; never real secrets, live databases or paid evaluations without explicit authorization.
- The reviewed recovery worktree unit gate passed on Python 3.11 (362 backend and 33 frontend tests); main remains the unrepaired red baseline. The required gameplay harness is blocked by provider availability, and hosted CI has not run. These local results do not authorize unattended FORGE task/plan/run, waive required checks, or establish release readiness. Retain the recovery roadmap's supervised scope and approval boundaries.

## Proposed by the loop

No additional invariants proposed during onboarding.
