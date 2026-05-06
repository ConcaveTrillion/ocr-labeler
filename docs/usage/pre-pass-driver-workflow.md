# Pre-Pass Driver Workflow

This document is the operational reference for the
`pd-ocr-labeler-driver` agent — the automated browser driver that
makes a fast, conservative first sweep over a project before a human
labeler opens it. It is also the audit trail: anyone reviewing what
the driver does (or is allowed to do) should be able to read this
page and confirm the behaviour against the running code.

## 1. Purpose and scope

A **pre-pass** is a low-risk, high-throughput sweep over every page
in a labeled project. It applies a small whitelist of mechanical
fixes — ligature normalization, long-s normalization, whitespace
cleanup, single-line OCR-to-GT copy on clean matches, and one
page-scope bbox refine — then saves the page and moves on. It exists
to eliminate the dull keystrokes a human would otherwise spend on
unambiguous mechanical edits, so that the human review pass can focus
on the genuinely ambiguous cases.

A pre-pass is **not** a labeling pass. It must not validate words,
must not merge across lines, must not touch OCR configuration, and
must not make any edit that requires reading more than the single
word or single line being changed. If the rule is not on the
whitelist in section 5, the driver leaves the page alone.

The audience for this doc is twofold:

- The driver agent reads it to know which selectors to drive, which
  rules to apply, and which footguns to avoid.
- Human reviewers read it to confirm the driver only does what it
  says, and to extend the rule set when a new mechanical case
  surfaces.

## 2. Selector inventory

Test IDs (`data-testid`) are the contract between the labeler UI and
the driver. The driver must address controls by testid where one
exists. If a needed testid is missing, the driver logs the gap (see
section 9) for backfill in the UI; it must not silently fall back to
a brittle CSS path that will break on the next refactor.

There is no aggregate "scope row" testid; the toolbar is a grid where
each individual action button at each scope (Page / Paragraph / Line /
Word) carries its own testid. The driver should target the specific
action button, not the row.

| Element                                        | Selector                                                | Used for                                              |
|------------------------------------------------|---------------------------------------------------------|-------------------------------------------------------|
| Page-scope Refine Bboxes (toolbar)             | `[data-testid="page-refine-bboxes-button"]`             | Single page-wide bbox refine (rule 5.5).              |
| Page-scope Copy OCR→GT (toolbar)               | `[data-testid="page-copy-ocr-to-gt-button"]`            | Forbidden by section 7 except in full-page-certain cases; listed so the driver recognises and avoids it. |
| Per-line `OCR→GT` button (line card)           | `[data-testid="line-ocr-to-gt-button"]`                 | Per-line OCR-to-GT shortcut on clean matches (rule 5.4). |
| Line card                                      | `[data-testid="line-card"]`                             | Iterating lines on a page.                            |
| Word selection checkbox                        | `[data-testid="word-checkbox"]`                         | Selecting words for toolbar actions (the pre-pass does not use toolbar word selection, but the testid is the contract for any future expansion). |
| Per-word GT input                              | `[data-testid="gt-text-input"]`                         | Inline GT corrections (ligatures, long-s, whitespace).|
| Per-word Validate button (line card)           | `[data-testid="word-validate-button"]`                  | Forbidden — see section 7. Listed here so the driver recognises and avoids it. |
| Save Page                                      | role-and-name: `get_by_role("button", name="Save Page")` | Persisting page state. **No testid in source today** — recommend adding `save-page-button`. |
| Toast                                          | `.q-notification`                                       | Save confirmation / error surface (Quasar built-in).  |
| Loading overlay                                | `.q-loading`                                            | First-load OCR spinner; wait for it to clear (Quasar built-in). |
| Next page                                      | role-and-name: `get_by_role("button", name="Next")`     | Advancing the loop. **No testid in source today** — recommend adding `next-page-button`. |
| Previous page                                  | role-and-name: `get_by_role("button", name="Prev")`     | Backtracking on operator instruction only. **No testid in source today** — recommend adding `prev-page-button`. |
| Go To page                                     | role-and-name: `get_by_role("button", name="Go To:")`   | First-page jump on driver start. **No testid in source today** — recommend adding `goto-page-button`. |
| Rematch GT                                     | role-and-name: `get_by_role("button", name="Rematch GT")` | Forbidden — section 7. **No testid in source today** — recommend adding so the driver can defensively assert it isn't present at click coordinates. |
| Reload OCR                                     | role-and-name: `get_by_role("button", name="Reload OCR")` | Forbidden — section 7. **No testid in source today** — recommend adding. |

GT-to-OCR no longer exists in the labeler UI. The reverse copy was
removed; the driver must not look for it and must not synthesise it
out of other primitives.

If `page-refine-bboxes-button` or any of the per-line
`line-ocr-to-gt-button` shortcuts cannot be located on a given build,
treat that as a stop-the-loop condition rather than guessing — log
the missing selector, move to the next project (or halt, see
section 4), and report it back so the testid can be re-confirmed or
added.

The role/name fallbacks listed above (Save Page, Next, Prev, Go To,
Rematch GT, Reload OCR) are tolerated for now because the underlying
controls have no testids. If a button text changes upstream the
fallback will silently break, so each of those rows is also a
backfill candidate; the driver should log a `MISSING_TESTID:` note
(see section 9) the first time it falls back per run so the gap stays
visible.

## 3. End-to-end loop

The driver processes pages sequentially. The loop body, in
pseudocode, is:

```text
for each page in project:
    navigate to page
        # role/name "Next" on subsequent iterations,
        # role/name "Go To:" on the first iteration
    wait for .q-loading to disappear
    take browser_snapshot

    # Page scope: one mechanical pass over bboxes
    click [data-testid="page-refine-bboxes-button"]

    for each [data-testid="line-card"] on the page:
        if OCR text and GT text are clean alphanumeric 1:1 matches
           AND the only difference is whitespace, ligatures, or long-s:
            click that card's [data-testid="line-ocr-to-gt-button"]
            continue

        for each word in the line:
            apply section 5 rules to [data-testid="gt-text-input"]
            commit with Enter

    record mtime of the page JSON before save
    click role/name button "Save Page"
    wait for .q-notification success toast (timeout: 10s)
    confirm page JSON mtime advanced past the recorded value
    write per-page log entry

    click role/name button "Next"
```

The driver runs strictly sequentially within a page. It does not
parallelise word edits, does not race the toast, and does not chain
into the next page until the save has been verified on disk.

## 4. Save and on-disk verification

Saved page state lives at:

```text
${XDG_DATA_HOME:-$HOME/.local/share}/pd-ocr-labeler/labeled-projects/<project>/<basename>.json
```

`<project>` is the project directory name, `<basename>` is the page
image filename without extension.

Before clicking **Save Page**, the driver reads the current mtime of
that JSON file (or notes that it does not yet exist). After the save
toast appears, the driver re-stats the file and confirms either the
file now exists or the mtime has advanced. A toast without an mtime
delta is treated as a save failure.

If the success toast does not appear within ten seconds of the click,
the driver:

1. Captures `browser_console_messages` for diagnostics.
2. Captures a `browser_snapshot` of the current DOM state.
3. Stops the loop — does not advance to the next page.
4. Surfaces the failure via the run report in section 10, including
   the project name, page basename, console messages, and the
   testids it was driving when the save was attempted.

This is the only time the driver halts mid-project. Recoverable
issues (a single skipped page because no rule fired, for instance)
do not stop the loop.

## 5. Pre-pass rules whitelist

These are the only edits the driver is allowed to make. Each rule is
local to a single word or single line and requires no semantic
understanding of context.

### 5.1 Ligature normalization

Replace the following Unicode code points in any GT word with their
ASCII expansion:

| Codepoint | Glyph | Replacement |
|-----------|-------|-------------|
| U+FB00    | ﬀ     | `ff`        |
| U+FB01    | ﬁ     | `fi`        |
| U+FB02    | ﬂ     | `fl`        |
| U+FB03    | ﬃ     | `ffi`       |
| U+FB04    | ﬄ     | `ffl`       |
| U+FB05    | ﬅ     | `ft` (long-s + t; replace with `ft`) |
| U+FB06    | ﬆ     | `st`        |

The replacement is unconditional for these codepoints. They do not
carry typographic meaning the labeler cares about, so normalising
them is always safe.

### 5.2 Long-s normalization

Replace `ſ` (U+017F, long-s) with `s` in GT text — but only when the
project is confirmed to be a long-s book. The confirmation must come
from the operator at run-start; the driver does not infer it from
content.

Caveat: `ß` (U+00DF, eszett) historically derives from `ſz`/`ſs` but
is **not** a long-s and must never be touched by this rule. The rule
operates on U+017F only.

When the project is not confirmed as long-s, this rule is disabled
in full. Do not apply it speculatively.

### 5.3 Whitespace strip and collapse

For each touched GT word:

- Strip leading and trailing ASCII whitespace.
- Collapse internal runs of ASCII whitespace to a single space.

Do not introduce or remove word boundaries — this rule operates on
the contents of one `gt-text-input`, not across inputs.

### 5.4 Per-line OCR-to-GT on clean 1:1 matches

When a line's OCR and GT are already a clean alphanumeric 1:1 match
(same word count, same word boundaries, differences only in the
shapes covered by 5.1, 5.2, or 5.3), click that line card's
`[data-testid="line-ocr-to-gt-button"]` instead of editing words
individually. This is a performance shortcut, not a different rule —
the resulting GT must be identical to what per-word application of
5.1–5.3 would produce.

Note: the per-line shortcut button only appears on lines whose
overall match status is not already `EXACT`. If the button is absent
on a line, the GT is already in sync with OCR and no action is
required.

If the line has any structural mismatch — different word count,
different segmentation, punctuation drift, hyphenation, or a word
that fails the alphanumeric check — fall back to per-word editing
under 5.1–5.3, or skip the line entirely.

### 5.5 Page-scope Refine Bboxes

Click `[data-testid="page-refine-bboxes-button"]` exactly once per
page, at the start of the page (before any per-line or per-word
work). This is the only bbox operation the pre-pass performs.

## 6. Things to leave alone

The following are explicitly out of scope for the pre-pass. They
require human judgement or cross-line reading and must be left for
the human pass:

- Smart quotes (`“ ” ‘ ’`) and dashes (`– —`). Do not normalise to
  ASCII; the labeler treats these as meaningful.
- End-of-line hyphens. Never auto-merge a hyphenated word across
  lines — the decision depends on whether the hyphen is lexical or
  line-break, and the driver cannot tell.
- Anything that requires reading beyond the current word or line:
  paragraph-level reflow, footnote markers, header/footer detection,
  style tagging.
- Punctuation cleanup of any kind beyond the whitespace rule in 5.3.
- Capitalization changes.

If a rule is not in section 5, it is in this section by default.

## 7. Hard rules and footguns

These are non-negotiable. Violating any of them in a pre-pass run is
a defect.

- **Never click `[data-testid="word-validate-button"]`** (the per-word
  validate icon on a line card) **or any of the toolbar variants**
  (`page-validate-button`, `paragraph-validate-button`,
  `line-validate-toolbar-button`, `word-validate-toolbar-button`,
  `line-validate-button`). Validation is a human signal. The pre-pass
  leaves every touched word unvalidated.
- **Never click the Rematch GT button** (role/name "Rematch GT", no
  testid in source today). It overwrites per-word GT edits and
  destroys human work that may already exist on the page.
- **Never click the Reload OCR or Reload OCR (Edited) buttons**
  (role/name "Reload OCR" / "Reload OCR (Edited)", no testid in
  source today). They re-run OCR and discard in-memory state
  including the driver's own edits.
- **Never click any delete button** at any scope. Concretely, avoid
  `[data-testid="line-delete-button"]`,
  `[data-testid="line-delete-toolbar-button"]`,
  `[data-testid="paragraph-delete-button"]`,
  `[data-testid="word-delete-button"]`, and the dialog-level
  `[data-testid="dialog-delete-word-button"]`. The pre-pass does not
  remove content.
- **Never open OCR Configuration and never trigger a re-OCR.** The
  pre-pass works with whatever OCR the project already has.
- **Page-scope Copy OCR→GT** (`[data-testid="page-copy-ocr-to-gt-button"]`)
  **is allowed only with full-page certainty** that the entire OCR
  text is correct. In practice this means the driver does not use it
  — the per-line shortcut from 5.4 covers the safe cases.
- **Do not open a second tab.** The driver runs in one tab against
  one server. A second tab fights for the same page state and
  produces inconsistent saves.
- **First-page slowness is expected.** The first page in any project
  loads OCR models and runs OCR on the page; this can take tens of
  seconds. It is not an error and does not warrant a stop.

## 8. Flagging discipline

The labeler exposes one flag per word: `validated` (boolean). There
is no "needs review", "auto-edited", or other side channel.

The pre-pass policy is:

- Touched words remain **unvalidated**. The human pass will validate
  them after review.
- Do not write any sentinel string into GT to mark driver-touched
  words ("[auto]", "TODO", trailing markers, etc.). GT must contain
  only the corrected text.
- Never call any auto-validation path, whether per-word, per-line,
  per-paragraph, or per-page.

The result is that, after a pre-pass, the human's **Unvalidated**
filter still shows every word the driver touched, in the same way it
would show every word a human had typed but not yet ticked off.

## 9. Per-session log

The driver writes one log file per run at:

```text
/tmp/pd-ocr-labeler-driver/<UTC-timestamp>.log
```

`<UTC-timestamp>` is `YYYYMMDDTHHMMSSZ`. The directory is created if
it does not exist.

Per page, append one block in this terse format:

```text
[<UTC-timestamp>] page=<basename>
  rules: ligature=<n> longs=<n> whitespace=<n> line_o2g=<n> bbox_refine=<0|1>
  saved: ok|fail  mtime_delta: <seconds>|n/a
  notes: <free-form one line, e.g. "skipped: structural mismatch on 3 lines">
```

One block per page. No multi-line free text beyond the single
`notes:` line. Missing testids are recorded under `notes:` with the
prefix `MISSING_TESTID:` so they can be grepped out for backfill.

## 10. Reporting contract

At end of run, the driver returns to the operator a single report
covering the whole project:

- **Pages processed:** `<n>` of `<total>`.
- **Per-rule counts**, summed across pages, in this phrasing:
  - `Ligatures normalised: <n> across <p> pages.`
  - `Long-s normalised: <n> across <p> pages.` (or
    `Long-s rule disabled (project not confirmed long-s).`)
  - `Whitespace cleaned: <n> across <p> pages.`
  - `Lines fast-pathed via OCR-to-GT: <n> across <p> pages.`
  - `Page bbox refines: <n>.`
- **Pages skipped**, each with the basename and a one-line reason
  (`no rule fired`, `structural mismatch on every line`, `save
  verification failed`, etc.).
- **Log path:** the absolute path to the per-session log from
  section 9.

The report is plain text. It is the only artefact besides the saved
page JSONs and the log file.

## 11. Sanity expectations

Use these baselines to decide whether the run is healthy:

- **Clean page:** a page with mostly clean OCR and a handful of
  ligatures or whitespace fixes should complete (navigate → refine →
  edits → save → verify) in single-digit seconds, plus toast wait.
- **Heavy page:** a page with dozens of edits should still complete
  in under a minute.
- **First page only:** model load and first-page OCR can take tens
  of seconds. Subsequent pages should not.
- **Stop signal:** if a page in steady-state (i.e. not the first
  page of the project) takes more than roughly 90 seconds end to
  end, stop the loop, capture a `browser_snapshot` and
  `browser_console_messages`, and surface it. Something is wrong
  — likely an unexpected modal, a stuck spinner, or a save that is
  not toasting — and continuing will only multiply the problem.

A healthy pre-pass run is boring: navigate, refine, type, save,
toast, advance. Anything more interesting than that is worth
stopping to look at.
