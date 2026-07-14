---
kind: index
status: active
owner: repository maintainers
created: 2025-08-21
last_verified: 2026-07-14
---

OCR Labeler (NiceGUI UI)
========================

> **Status:** This maintained NiceGUI application is being phased out in favor
> of `pd-ocr-labeler-spa`. Use this repository for the supported legacy
> workflow and consult the roadmap before starting new product work here.

Web UI for navigating OCR page images, reviewing overlays, and editing
OCR output against ground truth text. Built with
[NiceGUI](https://nicegui.io/) and a lightweight state layer that
lazily loads and OCRs pages via
[`pd-book-tools`](https://github.com/ConcaveTrillion/pd-book-tools).

Install
-------

One-line install (Linux / macOS):

```sh
curl -sSL https://raw.githubusercontent.com/ConcaveTrillion/pd-ocr-labeler/master/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/ConcaveTrillion/pd-ocr-labeler/master/install.ps1 | iex
```

Then run from any folder containing page images:

```sh
pd-ocr-labeler-ui .
```

Full install options (CUDA detection, install from source,
uninstalling, updating) → [`docs/usage/installing.md`](docs/usage/installing.md).

Use
---

Walk-through for opening a project, navigating pages, reviewing
overlays, editing words/lines/paragraphs, tagging styles, and saving →
[How to Label a Page](docs/usage/how-to-label-a-page.md).

Develop
-------

Setup, Make targets, working against a local `pd-book-tools` checkout
via `uv.toml`, and release flow → [`DEVELOPMENT.md`](DEVELOPMENT.md).

Architecture
------------

- [Architecture index](docs/architecture/README.md) — code map, NiceGUI
  patterns, async, multi-tab session isolation, threading, model
  alignment.
- [Planning / roadmap](docs/plans/README.md) — phased feature list
  and editing roadmap.

AI agent docs
-------------

`AGENTS.md` is the canonical instruction file for AI coding agents
working in this repo (Copilot, Claude Code, etc.).

Doc retrieval order (for AI prompts)
------------------------------------

1. `README.md` (this file).
2. [`docs/usage/README.md`](docs/usage/README.md) — end-user behavior.
3. [`docs/architecture/README.md`](docs/architecture/README.md) —
   internals.
4. [`docs/plans/README.md`](docs/plans/README.md) — roadmap.
5. [`docs/architecture/nicegui-patterns.md`](docs/architecture/nicegui-patterns.md)
   for NiceGUI behavior.
6. [`docs/architecture/async/overview.md`](docs/architecture/async/overview.md)
   and
   [`docs/architecture/async/migration-patterns.md`](docs/architecture/async/migration-patterns.md)
   for async behavior.

Treat docs as the source of truth; if implementation changes behavior,
update the matching doc.

License
-------

No project license has been published yet.
