# Spec-first AI development

Status: active
Date: 2026-09-21
Repository: `bhrumom/fabushi-marketplace`
Repository scope: official marketplace catalog, package metadata and marketplace-specific behavior

## Rule

**No Spec, No Code.** Read a durable applicable Spec before product-affecting implementation. If none exists, create `docs/specs/<task-name>.md` from `docs/specs/SPEC_TEMPLATE.md` before implementation.

Read-only discovery may precede the Spec only to understand current state and author/repair it.

## Repository identity

This repository is authoritative only for the scope above. Work owned elsewhere must switch repositories before implementation. Legacy copies in `bhrumom/fabushi` are migration/reference material.

## Minimum Spec

Define context/problem, goal, non-goals, requirements, current/target state, architecture/ownership boundaries, interfaces/contracts/data flow when relevant, non-functional constraints, failure modes, implementation strategy, verification, acceptance criteria/Definition of Done, release/migration/rollback/observability when applicable, and references/provenance.

## Lifecycle

Discover → Spec → Architecture/Plan → Implement → Verify → Spec Compliance Review → Integrate/Deliver.

For each requirement/AC, record `passed`, `blocked`, or `not-applicable` with evidence/reason before completion. Update the durable Spec whenever the latest explicit user requirement intentionally changes scope/design/behavior.
