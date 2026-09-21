# Fabushi Marketplace — Agent Instructions

These instructions apply repository-wide to AI-assisted development in `bhrumom/fabushi-marketplace`.

## CRITICAL: Repository ownership

This repository is the canonical source for **official marketplace catalog, package metadata and marketplace-specific behavior**.

Verify repository identity before product-affecting work. If the task belongs to another Fabushi repository, switch there before editing. `bhrumom/fabushi` is a legacy migration/source-history repository and is not an alternate implementation location for this scope.

## CRITICAL: Spec-first development — No Spec, No Code

Before changing product/runtime code, tests, schemas, contracts, dependencies, build/release configuration, migrations, security controls, or other behavior-affecting files:

1. Read this `AGENTS.md`.
2. Find and read the applicable durable Spec/project/source-of-truth.
3. Check `docs/specs/`.
4. Reconcile the Spec with the latest explicit user requirement and live repository facts.
5. If no usable Spec exists, or it is stale/unclear/contradictory, create or repair the Spec before implementation using `docs/specs/SPEC_TEMPLATE.md`.

Read-only investigation needed to understand the current state or write the Spec is allowed first. Product implementation is not.

## Mandatory lifecycle

**Discover → Spec → Architecture/Plan → Implement → Verify → Spec Compliance Review → Integrate/Deliver**

Before completion, compare the final implementation against every requirement/acceptance criterion and record `passed`, `blocked`, or `not-applicable` with evidence/reason.

Do not use chat memory as the only durable requirement source, silently change scope, weaken acceptance criteria, or leave intentional behavior/design changes undocumented.

Canonical policy: `docs/specs/spec-first-ai-development.md`.
