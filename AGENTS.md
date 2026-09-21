# AGENTS.md

This document defines global rules for AI coding agents working in this repository.

Rules exist only to prevent real defects.

---

## Rule 1 — Read Before Writing

Before adding or changing code, read:
- target file
- direct callers
- exports
- nearby shared utilities

Prevents:
- duplicate helpers
- broken exports
- ignoring existing local patterns

---

## Rule 2 — State Assumptions

If behavior is ambiguous:
- state assumptions first
- ask instead of guessing when needed

Prevents:
- wrong API behavior
- wrong UI flow
- incorrect business logic

---

## Rule 3 — Prefer The Smallest Working Change

Solve problems with the least code necessary.

Do not:
- over-engineer
- introduce abstractions for one-off logic
- redesign architecture unnecessarily

Prevents:
- unnecessary complexity
- large blast radius
- harder future maintenance

---

## Rule 4 — Make Surgical Edits

Touch only files and lines required for the task.

Do not:
- reformat unrelated code
- rename unrelated symbols
- refactor unrelated logic

Prevents:
- noisy diffs
- accidental regressions
- overwritten user changes

---

## Rule 5 — Reuse Existing Components First

Check for existing shared components/utilities before creating new ones.

Prevents:
- duplicated UI
- duplicated helpers
- inconsistent behavior

---

## Rule 6 — Follow Local Style

Match the style already used in the repository.

Do not introduce:
- new frameworks
- new styling systems
- new architectural patterns
without clear reason.

Prevents:
- mixed coding styles
- dependency sprawl
- inconsistent codebase structure

---

## Rule 7 — Use Existing Design/System Tokens

Use existing:
- theme tokens
- spacing rules
- typography
- colors
- shared constants

Avoid hardcoded values when equivalents exist.

Prevents:
- design drift
- inconsistent UI
- duplicated constants

---

## Rule 8 — Expose Pattern Conflicts

If multiple patterns exist:
- choose the dominant/local pattern
- explain conflicts clearly
- do not invent hybrid patterns

Prevents:
- inconsistent implementations
- mixed conventions
- fragile code paths

---

## Rule 9 — Define Done Before Iterating

Before complex work:
- define what success means
- verify behavior before declaring completion

Prevents:
- incomplete fixes
- fake completion
- unverified behavior

---

## Rule 10 — Test The Intent

Tests should validate:
- business behavior
- user intent
not implementation details only.

Prevents:
- meaningless tests
- passing tests with broken behavior

---

## Rule 11 — Fail Loudly

Never present:
- partial work
- skipped steps
- uncertain results as success.

Clearly state:
- what failed
- what was not verified
- what depends on external systems

Prevents:
- false confidence
- silent failures
- hidden risks

---

## Rule 12 — Preserve Backwards Compatibility

Do not break:
- APIs
- configs
- environment variables
- file structure
unless explicitly instructed.

Prevents:
- integration breakage
- deployment failures
- upgrade regressions

---

## Rule 13 — Record User-Visible Changes

For every user-visible feature, behavior fix, or format-parser correction:
- add a concise entry under `CHANGELOG.md` → `[Unreleased]`
- update the relevant technical documentation when behavior or format
  understanding changed

Prevents:
- completed fixes existing only in commit history or internal audit notes
- release notes drifting away from shipped behavior
