# Next Step: Browser Test Coverage Expansion

**Status:** Not Started

Goal: expand browser test coverage from 28% to 97% of 107 UI buttons
using the 14-commit phased plan in
[browser-ui-test-plan.md](browser-ui-test-plan.md).

## Priority Order

1. Toolbar scope actions (line + word rows) — 0% currently
2. Word edit dialog operations (merge/split/crop/refine/nudge) — 0%
3. Per-line action buttons (OCR→GT, Validate, Delete) — 0%
4. Source folder dialog — 0%
5. Header/load controls — 11%
6. Keyboard shortcuts — 0%
7. Image tab controls — 0%

## Done Criteria

- All 14 commits from the browser test plan are implemented.
- `make test-browser` passes reliably with `pytest -n auto`.

---

## Roadmap: Stable data-testid Backfill on Load-Bearing Controls

**Status:** In Progress — Page Actions complete (see Done entry below).
Project navigation controls (`Prev` / `Next` / `Go To:`) and any
remaining load-bearing controls still pending.

### Symptom (testid backfill)

The new `pd-ocr-labeler-driver` agent (and any future Playwright-based
automation) needs stable selectors. Several load-bearing controls
today have only visible-text labels, which drift over time and create
silent breakage when copy is reworded. The driver currently falls back
to `role` / accessible-name lookups for these — works, but brittle:
any label rename silently turns a click into a no-op or, worse, a
mis-click on a similarly named control.

### Controls Missing a `data-testid`

| Control label         | Source                                                                  | Proposed testid           | Status |
|-----------------------|-------------------------------------------------------------------------|---------------------------|--------|
| `Save Page`           | `pd_ocr_labeler/views/projects/pages/page_actions.py`                   | `save-page-button`        | Done   |
| `Save Project`        | `pd_ocr_labeler/views/projects/pages/page_actions.py`                   | `save-project-button`     | Done   |
| `Load Page`           | `pd_ocr_labeler/views/projects/pages/page_actions.py`                   | `load-page-button`        | Done   |
| `Reload OCR`          | `pd_ocr_labeler/views/projects/pages/page_actions.py`                   | `reload-ocr-button`       | Done   |
| `Reload OCR (Edited)` | `pd_ocr_labeler/views/projects/pages/page_actions.py`                   | `reload-ocr-edited-button`| Done   |
| `Rematch GT`          | `pd_ocr_labeler/views/projects/pages/page_actions.py`                   | `rematch-gt-button`       | Done   |
| `Next`                | `pd_ocr_labeler/views/projects/pages/project_navigation_controls.py:44` | `next-page-button`        | Pending|
| `Prev`                | `pd_ocr_labeler/views/projects/pages/project_navigation_controls.py:42` | `prev-page-button`        | Pending|
| `Go To:`              | `pd_ocr_labeler/views/projects/pages/project_navigation_controls.py:46` | `goto-page-button`        | Pending|

### Desired End State (testid backfill)

- Every load-bearing control in the labeler UI carries a stable
  `data-testid`.
- The driver agent and Playwright tests select by testid, never by
  visible text.
- Naming convention follows the existing pattern
  (`<scope>-<action>-button`).

### Scope Notes (testid backfill)

- Trivial mechanical change per button:
  `.props(f"data-testid='<name>'")`.
- Update `docs/architecture/ui-action-buttons.md` so the table of
  buttons records each new testid alongside the label.
- Update the relevant browser/unit test files to select by testid
  rather than visible text where they currently do the latter.
- Two concrete reasons to actually do this work:
  1. The driver agent's contract becomes stable across UI copy
     changes.
  2. `Rematch GT` and `Reload OCR` are *forbidden* controls for the
     driver — defensively detecting them by testid lets the driver
     hard-fail with a clear message instead of mis-clicking under a
     renamed label.

---

## Previously Completed Next Steps

### Stable data-testid Backfill — Page Actions (Done)

`PageActions` buttons now carry `data-testid` props for stable
selection from Playwright tests and the
`pd-ocr-labeler-driver` agent: `reload-ocr-button`,
`reload-ocr-edited-button`, `save-page-button`,
`save-project-button`, `load-page-button`, `rematch-gt-button`.
Browser tests in `tests/browser/test_page_actions.py` migrated from
accessible-name selectors to testid selectors. Architecture-doc
button table in `docs/architecture/ui-action-buttons.md` updated to
record each new testid alongside the label. Navigation controls
(`Prev` / `Next` / `Go To:`) and other load-bearing controls remain
on the testid backfill backlog for follow-up iterations.

### Default Projects Folder + Test Isolation (Done)

Persistence layer (`ConfigOperations`, `SessionStateOperations`) reads
XDG dirs at call time, so tests redirect `XDG_CONFIG_HOME` /
`XDG_DATA_HOME` / `XDG_CACHE_HOME` to a tmp tree via a session-scoped
autouse fixture in `tests/conftest.py`; browser-test subprocesses get
the same env in `tests/browser/conftest.py`. Two regression tests in
`tests/pd_ocr_labeler/operations/persistence/test_persistence_isolation.py`
assert no leakage to the real user home. The in-container default
projects folder
(`/home/vscode/.local/share/pd-ocr-labeler/source-pgdp-data/output`)
is provided by a nested bind mount in `.devcontainer/devcontainer.json`
overlaying `${localWorkspaceFolder}/source-pgdp-data`.

### Session Restore (Done)

`SessionStateOperations` saves project path and page index on every
project load; at startup, when no CLI project is provided, the saved
session is restored via `_try_restore_session` in `app.py`.

### Multi-JSON Ground Truth Merge (Done)

`pages_manifest.json` support in `ProjectOperations.load_ground_truth_from_directory`.
Manifest lists source files with optional numeric page-key offsets (e.g. `{"file": "pages_r2.json", "offset": 100}`).
Fell back gracefully to `pages.json` when no manifest exists.

### Add-Word Workflow (Done)

`LineOperations.add_word_to_page` inserts a new `Word` with drawn bbox into the
nearest line. `PageState.add_word` exposes it through the state layer. Toolbar
"Add Word" button triggers image-tab draw mode; drawn rectangle is propagated
back via `ContentArea` callbacks to `WordMatchBbox.apply_add_word_bbox`.

### Save Project — Bulk Page Persist (Done)

Implemented `save_all_pages()` in `ProjectState` with `SaveProjectResult`
tracking. "Save Project" button wired in `PageActions` with notification
summary. Reuses existing `persist_page_to_file` infrastructure.

- Notification shows save summary (saved/skipped/failed counts).
- No regression in existing per-page Save Page behavior.
- At least one unit test validates the bulk save flow.

---

## Previously Completed Steps

- Per-Word Validation State with Line/Paragraph Rollup (Done)
- Preserve Per-Word GT Edits Across Save/Load (Done)
- Ground Truth PGDP Preprocessing (Done)
