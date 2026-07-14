---
kind: context
status: active
owner: repository maintainers
created: 2026-07-14
last_verified: 2026-07-14
---

# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** choosing work, checking deferred ideas, or avoiding rejected scope.
- **Search terms:** active work, deferred work, residual intent, owner decisions.

## Active

- Keep the current usage and architecture documentation aligned with code,
  tests, Make targets, and supported installation paths.
- Finish browser-level save/load round-trip coverage and the remaining export
  UI gaps described by the retained roadmap.

## Deferred

- Revalidate the `run.io_bound` ground-truth loading path for the documented
  `None` race before changing asynchronous page loads.
- Repair the ground-truth editor's Tab and Shift+Tab focus behavior, and verify
  the reported cross-line form-line `+2` discrepancy against current code.
- Make OCR configuration application atomic, with failure rollback, before
  expanding the configuration workflow.
- Revisit stale-closure, double-click, listener lifecycle, notification
  deduplication, URL/focus accessibility, and test-isolation risks.
- Clean up browser-helper timeout behavior and replace any tautological
  Ctrl-click coverage with assertions that prove the intended selection state.
- Decide whether word/line derived caching, disconnect flush, nearby-page
  prewarm, distribution variants, and dev-local dependency protection belong
  here or in a successor application. None is shipped behavior.
- Consider moving reusable crop, structural editing, bounding-box, style, and
  text-copy operations upstream to `pd-book-tools`; revalidate ownership and API
  shape first.
- Consolidate semantic browser selection helpers and preserve direct coverage
  for distinct line-split operations.
- Complete the remaining `pd-book-tools` Page-model alignment. Dynamic
  compatibility attributes and provenance fallbacks still exist in current
  source.

## Rejected

- Treating the May 2026 review inventories, subjective module ratings, command
  transcripts, or implementation checklists as current architecture.
- Presenting speculative remote GPU worker, queue, and scale-to-zero designs as
  shipped. The repository implements local in-process device selection instead.

## Owner decisions

None blocks this migration. Future prioritization between this NiceGUI app and
any successor remains a product-planning choice, not a documentation lifecycle
ambiguity.

## Evidence

- Archived-plan classification: commit `21f7eba`
- Deferred defect provenance: deleted `docs/archive/plans/next-step.md` and
  supporting May 2026 research, recoverable from git history and commit
  `21f7eba`.
- Persistence implementation: commit `2cf8465`
- Export implementation: commit `6987791`
- Current code and tests: `pd_ocr_labeler/`, `tests/`
