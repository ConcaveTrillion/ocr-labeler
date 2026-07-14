---
kind: context
status: active
owner: repository maintainers
created: 2026-07-14
last_verified: 2026-07-14
---

# Current state

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** starting repository work or checking current risks.
- **Search terms:** current implementation, active risks, verification.

The repository contains the maintained NiceGUI OCR-labeling application. Its
current behavior is documented by the [architecture index](../architecture/README.md),
and its supported commands are defined by the Makefile and `CLAUDE.md`.

The July 2026 baseline exposed browser-test synchronization debt. Project-load
helpers could return before asynchronous loading completed, CodeMirror tests
targeted private DOM, and the interactive-image host can have zero layout size
while its rendered source is ready. The migration updates those test contracts;
the full CI gate remains the completion authority.

Current partial work is limited to the items in the [intent map](intent-map.md).
No dated review pack or retired checklist is current implementation truth.

## Evidence

- Code: `pd_ocr_labeler/`
- Tests: `tests/`
- Commands: `Makefile`, `CLAUDE.md`
- Verified: 2026-07-14 during the docgraph migration
