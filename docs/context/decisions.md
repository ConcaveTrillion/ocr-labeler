---
kind: context
status: active
owner: repository maintainers
created: 2026-07-14
last_verified: 2026-07-14
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** checking durable rationale, changed direction, or retired topics.
- **Search terms:** decisions, tombstones, implementation deviations, retirement.

## 2026-07-14: Replace historical execution artifacts with current truth

The migration removes dated review packs, completed implementation plans, and
stale point-in-time inventories after preserving shipped behavior in
architecture and unresolved ideas in the [intent map](intent-map.md). Git
history remains the source for discarded transcripts and checklist detail.

Evidence: checker-derived legacy queue; commit `21f7eba`; current code and tests.

## 2026-07-14: Record implementation deviations explicitly

The unified overlay retained the `ImageTabs` compatibility surface. Persistence
shipped as schema 2.1 envelopes, OS-aware source lanes, atomic writes, and
session-state operations rather than the proposed local-data manifest. Page
provenance moved upstream while compatibility fallbacks remained. Remote GPU
workers did not ship; local in-process device selection did.

Evidence: `image_tabs.py`, `user_page_persistence.py`, `page_operations.py`,
`project_state.py`, and their tests.

## 2026-07-14: Retirement tombstones

The following documents were retired and deleted. The first migration commit
is recorded after the retirement wave lands. Current replacements and remaining
work are shown here.

| Old paths | Outcome | Replacement | Rationale kept | Remaining work |
| --- | --- | --- | --- | --- |
| `docs/archive/plans/**` (5 files) | retired | architecture and intent map | closed/partial outcomes from `21f7eba` | explicit deferred defects in intent map |
| `docs/archive/research/**` (21 files) | retired | architecture, decisions, intent map, code/tests | confirmed findings and changed direction | revalidate deferred risks before implementation |
| `docs/architecture/async/affected-files.md` | superseded | async overview and migration patterns | NiceGUI async constraints | none |
| `docs/architecture/doc-sync-tasks.md` | implemented | architecture index and intent map | unfinished Page alignment | deferred alignment |
| `docs/architecture/gpu-deployment.md` | abandoned | intent map and current install docs | local GPU direction | remote-worker idea deferred |
| `docs/architecture/ui-action-buttons.md` | superseded | browser tests and browser-testing architecture | stable test contracts | keep tests authoritative |
| `docs/plans/image-overlay-layer-controls-plan.md` | implemented | image-overlays architecture | compatibility-surface deviation | none |
| `docs/plans/pd-book-tools-page-provenance-copilot-brief.md` | implemented | persistence architecture and decisions | upstream ownership with compatibility fallbacks | complete remaining Page alignment |
| `docs/plans/user-persistence-metadata-schema.md` | implemented | persistence architecture | shipped schema and source-lane deviations | residual caching ideas in intent map |

The archive rows expand to these exact old paths:

- `docs/archive/plans/browser-ui-test-plan.md`
- `docs/archive/plans/next-step.md`
- `docs/archive/plans/roadmap/editing-core.md`
- `docs/archive/plans/roadmap/enhanced-ui-matching.md`
- `docs/archive/plans/roadmap/navigation-multi-page.md`
- `docs/archive/research/2026-05-06-async-handler-races.md`
- `docs/archive/research/2026-05-06-browser-test-selection-helpers.md`
- `docs/archive/research/2026-05-06-keyboard-shortcuts-coverage.md`
- `docs/archive/research/2026-05-06-monkeypatch-wiring-attempt.md`
- `docs/archive/research/2026-05-06-notification-mixin-dedup.md`
- `docs/archive/research/2026-05-06-ocr-config-modal-state-machine.md`
- `docs/archive/research/2026-05-06-toolbar-split-family.md`
- `docs/archive/research/code-review-README.md`
- `docs/archive/research/correction-plan.md`
- `docs/archive/research/dead-code.md`
- `docs/archive/research/duplicated-code.md`
- `docs/archive/research/found-gt-errors.md`
- `docs/archive/research/iteration-plan.md`
- `docs/archive/research/layer-violations.md`
- `docs/archive/research/module-ratings.md`
- `docs/archive/research/overnight-2026-05-06-summary.md`
- `docs/archive/research/pd-book-tools-candidates.md`
- `docs/archive/research/review-README.md`
- `docs/archive/research/review-architecture.md`
- `docs/archive/research/review-bugs.md`
- `docs/archive/research/style-inconsistencies.md`

Every row was removed by the retirement-wave commit recorded in the next
decision entry. The archive globs expand to the exact paths retained in that
commit's deletion diff.
