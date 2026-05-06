# Spec: Bottom-Crop Bbox Tool

Status: spec only — no implementation yet. Decision-oriented; intended
to be green-lit, push-back on, or revised before code is written.

Author intent: extend the existing bbox refinement family with a tool
that aggressively tightens the **bottom edge** of word bounding boxes
using image heuristics and the GT/OCR text of the word, on the
observation that very few Latin glyphs descend below the baseline.

## 1. Goal and scope

### Problem

OCR detection bboxes (DocTR in this codebase) frequently extend below
the actual ink of a word. Common causes:

- Vertical leading bleeding from the line below picked up as part of
  the detection box.
- Speckle, page-curl shadows, or bleed-through ink under the line.
- Tall original detections that included a descender zone, then the
  word turned out to have no descender.

The visible result is a bbox whose bottom is several pixels below
where the ink ends, which:

- Inflates training crops with negative space when these labels are
  exported as ground truth.
- Makes selection / hover regions overlap the line below, which is
  user-visible noise in the labeler.
- Breaks downstream layout heuristics that assume bbox bottom is
  near the baseline + descender depth.

The existing `refine_bbox` helper on `Word`
(`pd_book_tools/ocr/word.py:450`) already shrinks to the connected ink
inside the box, but it is uniformly tight on all four sides. A
top-tight crop is usually fine; a bottom-tight crop discards the
descender zone for words like "page" or "jury", which the user does
not want. The current tool therefore has to be conservative on the
bottom, which is exactly the case this spec wants to optimize.

### Goal

Provide a bbox-bottom tightening pass that:

- Uses the GT text (or, as a fallback, OCR text) of the word to
  decide whether the word **could** have a descender.
- For words known to have no descender, crops the bottom to the
  lowest detected ink row plus a small safety pad.
- For words with possible descenders, leaves room for descender ink —
  ideally measured against a per-line baseline rather than the word's
  own bbox top.

The output is a new bbox per word with a tighter (or equal) bottom
edge. The top, left, and right edges are not modified by this pass.

### Non-goals (v1)

- **Non-Latin scripts.** Cyrillic, Greek, Hebrew, Arabic, Devanagari,
  CJK — out of scope. The descender heuristic and the static
  descender character set are Latin-script assumptions. The tool
  should detect non-Latin content (e.g. via codepoint range) and
  refuse to act, not silently misbehave.
- **Top-cropping in the same pass.** The existing per-word `refine`
  already tightens the top reasonably. A separate top-crop tool can
  be considered later if the same use case appears, but folding it in
  here would muddy the spec and the heuristics differ
  (ascenders vs descenders, capitals vs no-capital words).
- **Side-cropping.** Existing refine handles left/right adequately.
- **Box growth.** This tool only ever shrinks the bottom edge or
  leaves it unchanged. It never extends the bbox bottom downward —
  that is the job of `expand_then_refine`.
- **Re-flowing layout.** No line splitting, no paragraph
  re-detection, no reading-order changes.

## 2. Heuristic design

### 2.1 Descender character set

Treat the following as the only Latin-script characters that may
extend meaningfully below the baseline (consistent with the existing
set in `pd_book_tools/ocr/word.py` baseline estimation:
`descender_chars = {"p", "g", "j", "q", "Q"}`):

- Lowercase: `g`, `j`, `p`, `q`, `y`
- Uppercase: `J`, `Q` (Q's tail, J's hook in many faces)
- Punctuation: `,` `;` `(` `)` `[` `]` `{` `}` `_` and the printer's
  underscore-style tail in some faces; comma and semicolon are the
  only ones that genuinely carry ink below the baseline. Parens
  bottoms tend to sit at the baseline, but in some serif faces dip
  slightly below; treat them as descender-bearing for safety.
- Long-s `ſ` does **not** descend.
- Old-style/text-figures digits (`3`, `4`, `5`, `7`, `9` historically
  in some faces) descend below the baseline. This is corpus-specific
  — see open question Q1 in section 9.

The existing pd-book-tools set is narrower (`p`, `g`, `j`, `q`, `Q`).
The spec proposes broadening it for this tool to:

```python
DESCENDER_CHARS = {
    "g", "j", "p", "q", "y",
    "J", "Q",
    ",", ";",
    "(", ")", "[", "]", "{", "}",
}
```

with old-style figures gated behind a corpus-level toggle (Q1).

A word "has a descender" if any character in its GT text (preferred)
or OCR text (fallback) is in `DESCENDER_CHARS`. The check is
codepoint-level on the raw string after ligature expansion (which the
labeler already does in the pre-pass).

### 2.2 Per-line baseline vs per-word ink scan

Two viable heuristic shapes:

**Option A — per-word ink scan only.** For each word: extract the
ROI, threshold, find the lowest row that contains ink, set bottom =
that row + small pad. If the word has a descender per 2.1, leave the
existing bottom alone (or only crop down to that ink row, not above
it).

Trade-off: simple, no cross-word state, no failure mode where one
mis-segmented neighbor poisons the rest of the line. But the
no-descender path leaves obvious slack when the OCR bbox already
included descender room — fine, that's the point of the tool. The
descender path is conservative: it keeps whatever the original bbox
gave us and so produces zero benefit on descender-bearing words.

**Option B — per-line baseline + descender allowance.** For each
line: estimate a baseline `y` (one float per line, in page-pixel
space). For each word in the line:

- If no descender: bottom = baseline + small_pad (or word's own
  lowest-ink row + small_pad, whichever is higher).
- If descender: bottom = baseline + descender_allowance, where
  `descender_allowance` is a fraction of the line's x-height
  (typically 0.3–0.4 * x-height, or measured per-page from actual
  descender words).

Trade-off: gives benefit on descender-bearing words too, and produces
visually consistent bottoms across the line, which matters for clean
training crops. Costs a per-line baseline estimation pass and
introduces a failure mode where a tilted line or a single tall
neighbor pulls the baseline off.

**Recommendation: Option B,** with per-word ink-scan as a fallback
when the per-line baseline confidence is low or the line has fewer
than ~3 words (where averaging is unreliable). pd-book-tools already
has the primitives we need:

- `Word.estimate_baseline_from_image`
  (`pd_book_tools/ocr/word.py:961`) — produces a per-word baseline_y
  with a confidence score, weighting descenders down. Aggregating
  these across a line gives a robust per-line baseline.
- `Word.split_into_characters_from_whitespace` already estimates
  x-height implicitly (via `median_height`).

The new code path should call into these existing helpers rather than
re-deriving them.

### 2.3 Fallback when GT text is empty

For a word with GT empty (OCR-only):

1. If OCR text is non-empty, use OCR text for the descender
   classification.
2. If OCR text is also empty (rare — usually means a stray
   detection), do not crop at all. Skip the word and log it.

Do **not** apply the more aggressive no-descender crop to OCR-text
words without explicit user opt-in — OCR text can be wrong, and
mis-classifying a word as descender-free will eat ink from a `g` or
`y`. The default policy is "treat OCR-text as truth, but if the bbox
is suspiciously short relative to its line's x-height, skip".

### 2.4 Ink detection

Use the same threshold pipeline as existing refine:
`BoundingBox._threshold_inverted`
(`pd_book_tools/geometry/bounding_box.py:835`) — grayscale → invert →
Otsu binary threshold. This is shared by `refine`, `crop_bottom`,
`crop_top`, and the existing word-level `refine_bbox`. Consistency
with the existing pipeline matters; this spec does **not** invent a
new image preprocessing pipeline.

The "lowest ink row" within a thresholded ROI is the existing logic
in `BoundingBox._vertical_crop(keep="top")` at
`pd_book_tools/geometry/bounding_box.py:611`. The new tool can reuse
that primitive directly.

Robustness concerns and the chosen mitigations:

- **Speckle below the line.** A single isolated dark pixel under the
  word would defeat "lowest ink row". Mitigation: require a minimum
  run-length (configurable, default 2 px) of horizontally connected
  ink in the candidate row before accepting it as the bottom. Or
  equivalently: morphologically open the threshold ROI by a small
  kernel before scanning. The existing `_vertical_crop` already does
  a row-adjacency check (rows must touch the row above to count) —
  this is the same idea and should be reused or extended.
- **Bleed-through.** Where bleed-through is bright enough to cross
  Otsu, this tool will misclassify it as descender ink and refuse to
  crop. Acceptable — bleed-through is a corpus-level problem the
  pre-processing pipeline should handle separately.
- **Italics leaning into the line below.** See section 6.

## 3. Integration choice

The user explicitly raised:

- (a) a new tool button alongside Refine Bboxes, e.g. "Crop Bottoms",
  or
- (b) folding into Refine Bboxes itself.

**Recommendation: (a) — a new, separate tool, at all four scopes
(page / paragraph / line / word).**

Reasoning:

1. **Refine already touches all four sides equally.** Folding a
   text-aware, baseline-aware bottom-only heuristic into `refine`
   would change the semantics of an existing widely-used button.
   Users (and the pre-pass driver) currently expect refine to be
   purely image-based and side-symmetric. Hiding GT-text-conditional
   logic behind that button will surprise people, and the failure
   mode ("why did refine eat my descender?") is hard to debug.
2. **Aggressiveness.** Bottom crop is more aggressive than refine on
   the no-descender case (it deliberately uses the GT text to crop
   tighter than image evidence alone would justify). That extra
   aggressiveness deserves its own button so users can choose to
   apply it or not.
3. **Driver granularity.** The pre-pass driver currently runs exactly
   one bbox-refine call per page (rule 5.5 in
   `docs/usage/pre-pass-driver-workflow.md`). Adding a second
   distinct mechanical step (`page-bottom-crop-button`) is cleaner
   than expanding what "refine" means and lets the driver enable or
   disable it per-project.
4. **Discoverability.** A separate icon next to refine
   (`auto_fix_high`) communicates "the other automatic bbox tool" to
   the human user. A magic-toggled refine does not.

Concretely the new toolbar button uses the same scope-grid pattern as
the existing operations
(`pd_ocr_labeler/views/projects/pages/word_match_toolbar.py`) and gets
its own column. Suggested icon: `vertical_align_bottom` or
`align_vertical_bottom` (Material Symbols both exist; pick whichever
renders in the app's icon set — see open question Q5).

Naming proposal:

- Tool: **Crop Bottoms** in the UI tooltip.
- Public method (pd-book-tools): `crop_word_bottoms_to_baseline` (see
  section 2.5 of this spec for placement).
- Test IDs: `page-crop-bottoms-button`, `paragraph-crop-bottoms-button`,
  `line-crop-bottoms-button`, `word-crop-bottoms-button` — consistent
  with existing `*-refine-bboxes-button` pattern.

### Pre-pass driver inclusion

**Recommendation: do not add to the pre-pass driver in v1.**

The driver's whitelist is deliberately conservative; a pass that
modifies bboxes based on text content (where text content can itself
be wrong on first OCR) is a category jump. Land the tool human-only,
gather a few weeks of usage, then revisit whether it qualifies for
rule 5.6. The pre-pass-driver-workflow doc should get a single line
explicitly listing **Crop Bottoms** as a Section 7 footgun (driver
must not click it) until that re-evaluation happens.

## 4. Scope of action

Mirror the existing scope grid: page / paragraph / line / word.

| Scope     | Behaviour                                                  |
|-----------|------------------------------------------------------------|
| Page      | Apply to every word on the page. Single per-line baseline pass per line. |
| Paragraph | Apply to every word in selected paragraphs.                |
| Line      | Apply to every word in selected lines.                     |
| Word      | Apply to selected word(s) individually. Per-line baseline still computed using all words on the host line, even when only one word is being cropped. |

UI placement: same scope grid as refine. The existing `BboxOperations`
class
(`pd_ocr_labeler/operations/ocr/bbox_operations.py`) is the obvious
home for the labeler-side iteration logic; it already has
`refine_words`, `refine_lines`, `refine_paragraphs` and the
`_apply_to_*` helpers. Add `crop_bottoms_words`, `crop_bottoms_lines`,
`crop_bottoms_paragraphs`, plus a page-level `crop_bottoms_page` that
goes through `PageOperations` for parity with `refine_all_bboxes` /
`expand_and_refine_all_bboxes` in
`pd_ocr_labeler/operations/ocr/page_operations.py`.

### Undo

Existing refine and expand-then-refine do not have explicit undo;
they rely on the user not having pressed Save Page, plus the
`original_page` snapshot kept in saved JSON. This tool should match:
no special undo, but it must respect the same "single page-scope
operation per click" granularity so that the user can compare
mentally before/after by toggling overlay images.

If/when the labeler grows a real undo stack, this tool participates
on the same terms as refine. The spec does not block on undo.

## 5. Safety: when to refuse to act on a word

The tool **must** skip a word (and log at debug level) in any of
these cases:

1. **Validated word.** If the word's `word_labels` contains
   `WORD_LABEL_VALIDATED` (per
   `pd_ocr_labeler/constants.py:WORD_LABEL_VALIDATED`), do not
   modify its bbox. Validation is the user's signal that the word
   is correct as-is, including its bbox.
2. **No image attached.** If `page.cv2_numpy_page_image` is None or
   the word's bbox cannot be extracted as an ROI, skip and log
   (mirror existing refine behaviour).
3. **Empty bbox or zero-width / zero-height.** Skip.
4. **Single-character word that is itself a descender.** A word like
   `,` or `;` is essentially all descender. Cropping it bottom-tight
   would erase it. Heuristic: if word text length is 1 **and** that
   character is in `DESCENDER_CHARS`, skip.
5. **GT text contains descender AND current bottom is already within
   one line-x-height + descender_allowance of the baseline.** No
   benefit from running, and the small-perturbation case introduces
   noise. The minimum-meaningful-crop threshold (Q4, Q7 in section
   7) covers this generically.
6. **No detectable ink in the ROI.** If thresholding finds no ink
   pixels, the word is either misdetected or below threshold; do
   not crop.
7. **Non-Latin codepoints in word text.** If the word's GT text
   contains characters outside Basic Latin + Latin-1 Supplement +
   Latin Extended-A/B (the project's working ranges), skip with a
   `non-latin: <text>` log. See Q2.
8. **Last line of a page where the line below is not present.**
   The tool's value is largely "remove leading from the line below".
   When there is no line below (last paragraph, footer, isolated
   caption), the OCR bbox is more often already correct. The tool
   should still run, but the `min-meaningful-crop` threshold
   (section 7) will naturally suppress no-op runs.

The first three are hard refusals. The last five are soft skips that
should be counted in a per-run summary (section 8).

## 6. Edge cases

- **Italics.** Italic words lean into the descender zone of the
  preceding word and out of their own bbox bottom-right. The
  per-word ink scan handles this correctly because we only care
  about the bottom edge, not where the descender pixel sits in x.
  The per-line baseline estimate is also robust because it averages
  across the whole line.
- **Long-s, ct-, st-ligatures.** None of `ſ`, `ﬅ`, `ﬆ`, `ct`, `st`
  carry ink below the baseline. They behave as no-descender
  characters. Confirm `ﬅ` (U+FB05) — visually it has a long-s, the
  long-s does not descend — treat as no-descender. After the
  pre-pass driver's ligature normalization (rule 5.1), most of these
  are already expanded to ASCII.
- **Punctuation-only "words".** A standalone `,` or `;` is mostly
  descender. Skip per safety rule 5.4. A standalone `.` is fine to
  crop tight (no descender). A standalone `(` or `)` is treated as
  a descender-bearing token by the proposed set; the safety rule
  catches the single-char case anyway.
- **Last-line-on-page.** Covered in 5.8.
- **Italics that lean into the line below.** Existing OCR detection
  already mostly handles this; if the tool does see ink that belongs
  to the *next* line's ascenders inside this word's ROI, the
  per-line baseline + safety pad approach will keep the crop above
  it because the line below's ascenders sit well below this line's
  baseline + descender allowance.
- **All-uppercase lines (e.g. headings) where there are no
  descenders at all.** The per-line baseline estimator weights
  by character height; with no descenders the result is essentially
  "lowest character bottom on the line", which is what we want.
  Crops should be visibly cleaner here than in mixed-case body text.
- **Hyphenated word at end of line.** Hyphen sits at x-height, no
  descender concern. Treat normally.

## 7. Tunable parameters

Defaults are decision-oriented; the implementation should expose them
as kwargs on the pd-book-tools function and as a (deferred) settings
panel in the labeler.

| Parameter                       | Default                  | Notes |
|---------------------------------|--------------------------|-------|
| `descender_allowance_px`        | `0.35 * line_x_height`   | How far below the baseline to leave room for descenders, when the word has a descender. Pixel value derived from per-line x-height. |
| `safety_pad_px`                 | `1`                      | Always added to the chosen bottom so we don't shave the last anti-aliased pixel of a glyph. |
| `min_crop_px`                   | `2`                      | Skip the operation entirely if the proposed bottom is within this many pixels of the current bottom. Avoids 1-px churn (which makes diffs noisy and bloats undo state). |
| `min_words_for_baseline`        | `3`                      | Below this word count on a line, fall back to per-word ink scan instead of per-line baseline. |
| `descender_chars`               | (set in section 2.1)     | Configurable per-corpus; old-style figures gated separately. |
| `oldstyle_figures_descend`      | `False`                  | When True, adds `3 4 5 7 9` to the descender set. Off by default; flip on for old-style figure books. |
| `ink_run_min_length_px`         | `2`                      | Minimum horizontal connected-ink run required for a row to count as ink (despeckle). |
| `ink_threshold_method`          | `"otsu"`                 | Reuse pd-book-tools default; allow `"adaptive"` later if needed. |
| `respect_validated`             | `True`                   | Whether to skip validated words. Off only for explicit "force re-crop" ops (not in v1 UI). |

The labeler UI does not need to expose these in v1 — a single button
with hardcoded sensible defaults is fine. Settings get a real home in
a later milestone.

## 8. Workflow: how a human or agent uses it

### Human workflow (v1)

1. Operator opens a page in the labeler. OCR is loaded.
2. Operator clicks the page-scope **Refine Bboxes** button (existing
   behaviour) for the symmetric ink-tightening pass.
3. Operator clicks the page-scope **Crop Bottoms** button (new) for
   the descender-aware bottom tightening.
4. Operator visually confirms via the bbox overlay that bottoms now
   sit just below the baseline / descenders.
5. If a single line/word looks wrong, operator can either:
   - Un-do at line scope by manually adjusting the bbox.
   - Click line- or word-scope **Crop Bottoms** with different
     selection (no different result, but explicit re-application is
     a no-op once `min_crop_px` is satisfied).
6. Operator clicks **Save Page**.

The result on disk is the same JSON shape as today — only word
bounding boxes have moved. No new schema fields are introduced.

### Agent workflow (deferred)

The pre-pass driver does **not** call this tool in v1. When v2
revisits driver inclusion:

- Add a new test ID `page-crop-bottoms-button` (already proposed in
  section 3) to the toolbar. The driver should be able to drive it
  by ID alone, just like `page-refine-bboxes-button`.
- Add a new whitelist rule (section 5.6 of pre-pass-driver-workflow,
  hypothetical): "After page-scope refine, click page-scope crop
  bottoms exactly once. If the project is confirmed Latin-script."
- Same logging and reporting conventions as existing rule 5.5
  (one-line per-page log entry, summary count in run report).

Until then, pre-pass-driver-workflow.md gets a single line under
section 7 (Hard rules and footguns):

> Never click `[data-testid="page-crop-bottoms-button"]` (or any
> scope variant). Bottom-crop is human-driven in v1; the driver does
> not exercise text-conditional bbox tools.

### What the user sees

- The button: an icon button next to Refine Bboxes in the same scope
  grid. Same `style_word_icon_button` styling.
- A tooltip: "Crop word bbox bottoms to baseline (Latin-script
  heuristic)".
- A toast on completion summarizing counts: e.g.
  `Cropped 84 words; skipped 6 (3 validated, 2 no-ink, 1 non-Latin).`
- Bbox overlay updates immediately (existing
  `refresh_page_images` path, which the existing refine operations
  already trigger).

## 9. pd-book-tools / pd-ocr-labeler split

This is mostly clean, modeled on how `refine_bbox` is split today.

### Lives in pd-book-tools

All image-processing primitives, baseline estimation, and per-word
crop logic. New surface area:

- `pd_book_tools.geometry.bounding_box.BoundingBox.crop_bottom_to_y(
  image, target_y, safety_pad_px=1, ink_run_min_length_px=2,
  )` — new pure-geometry helper that crops the bbox bottom to a
  given absolute y in image coordinates, snapped to the nearest ink
  row above `target_y` if there is ink within the safety pad. Uses
  the existing `_threshold_inverted` and the row-adjacency logic
  from `_vertical_crop`. **Unit-testable in isolation.**
- `pd_book_tools.ocr.word.Word.crop_bottom_to_baseline(
  image, baseline_y, has_descender, x_height,
  descender_allowance_frac=0.35, safety_pad_px=1, min_crop_px=2,
  )` — combines the descender flag + baseline + x-height into a
  target_y, then calls the BoundingBox helper. Returns True if the
  bbox actually changed. **Reuses existing
  `estimate_baseline_from_image` infrastructure for testing.**
- `pd_book_tools.ocr.block.Block.crop_word_bottoms_to_baseline(
  image, descender_chars=DEFAULT_DESCENDER_CHARS,
  use_gt_text_first=True, **kwargs,
  )` — line-level entry point. Estimates a single baseline_y and
  x_height for the block, classifies each word's text against
  `descender_chars`, calls the per-word helper. Returns the count of
  words actually changed plus a small per-skip-reason histogram.
  **The bulk of the heuristic logic lives here so it can be unit-tested
  without UI plumbing.**
- `pd_book_tools.ocr.page.Page.crop_word_bottoms_to_baseline(...)` —
  page-level convenience that loops over lines (or paragraphs ->
  lines, depending on page structure) calling the block-level method.
  Recomputes ancestor bboxes once at the end. Mirrors the shape of
  the existing `refine_bounding_boxes` page-level method
  (`pd_book_tools/ocr/page.py:2901`).
- `pd_book_tools.ocr.word.DEFAULT_DESCENDER_CHARS` (or similar
  module-level constant) — the set proposed in section 2.1.
  Currently the descender set is duplicated as a literal in two
  places in `word.py`; this spec is also a good occasion to dedupe.

### Lives in pd-ocr-labeler

Selection iteration, UI buttons, toast / log presentation, and
"respect WORD_LABEL_VALIDATED" policy. New surface:

- `pd_ocr_labeler.operations.ocr.bbox_operations.BboxOperations`
  gains `crop_bottoms_words`, `crop_bottoms_lines`,
  `crop_bottoms_paragraphs`, all calling into the pd-book-tools
  block/page-level functions through the existing `_apply_to_*`
  iteration helpers. The validated-word skip rule lives here, not in
  pd-book-tools — `WORD_LABEL_VALIDATED` is labeler vocabulary.
- `pd_ocr_labeler.operations.ocr.page_operations.PageOperations`
  gains `crop_bottoms_all_words(page)` mirroring `refine_all_bboxes`,
  for the page-scope toolbar button.
- `pd_ocr_labeler.views.projects.pages.word_match_toolbar` adds the
  four toolbar buttons (page / paragraph / line / word) with the
  test IDs from section 3.
- `pd_ocr_labeler.views.projects.pages.word_match_actions` adds the
  four `_handle_crop_bottoms_*` action methods, in the same shape
  as the existing `_handle_refine_*`.
- `pd_ocr_labeler.viewmodels.project.project_state_view_model` gets
  the callback wiring.
- Tests under `tests/` for the iteration + UI plumbing; the heavy
  heuristic tests (with synthetic images of known descender / no-
  descender words) live in pd-book-tools' `tests/ocr/`.

### Validation against existing pd-book-tools migration list

The labeler's
`docs/planning/code-review/pd-book-tools-candidates.md` already lists
"All bbox refinement and expansion methods" as candidates for
pd-book-tools. This new tool is in the same family and lands directly
in pd-book-tools — no labeler-only image code introduced.

## 10. Test plan (sketch)

Section 10 is the high-level sketch. The detailed plan, including
where each test class lives in the existing tree and what fixtures it
reuses, is in section 11. Section 12 covers CI integration.

In pd-book-tools:

- Unit: `BoundingBox.crop_bottom_to_y` against synthetic images with
  drawn glyphs at known y-positions. Cases: ink directly at target,
  ink above target, ink below target (should snap up to ink row),
  no ink (no change).
- Unit: `Word.crop_bottom_to_baseline` with descender / no-descender
  / single-char-descender / non-Latin text inputs.
- Unit: `Block.crop_word_bottoms_to_baseline` with a synthetic
  multi-word line: half descender-bearing, half not. Assert
  per-line baseline is the average, descender words keep room,
  non-descender words crop tight.
- Property: applying the operation twice is a fixed point (idempotent).

In pd-ocr-labeler:

- Unit: `BboxOperations.crop_bottoms_words` skips
  `WORD_LABEL_VALIDATED` words.
- Unit: page-scope `crop_bottoms_all_words` returns False when image
  is missing.
- Browser regression: clicking `page-crop-bottoms-button` measurably
  shrinks at least one bbox bottom on a fixture page that has known
  no-descender lines. Visual diff via existing Playwright pattern.

## 11. Testing strategy

Concrete test plan, mapping each new function/UI surface from
sections 3 and 9 to a place in the existing test tree.

### 11.1 pd-book-tools side

#### `BoundingBox.crop_bottom_to_y` — pure geometry

Lives next to existing crop tests in
`pd-book-tools/tests/geometry/test_bounding_box.py`
(see `test_crop_bottom_*` and `test_vertical_crop_branch_coverage` at
lines 1022–1109; same fixture / parametrize style). Cases:

- `target_y` strictly above the current bottom and inside ink rows:
  bottom snaps to the lowest ink row at or below `target_y` plus
  `safety_pad_px`.
- `target_y` at or below the current bottom: bbox unchanged
  (monotonicity — bottom never moves down).
- ROI has no ink: bbox unchanged, debug log emitted.
- ROI is all ink (solid block, e.g. an underline): bottom unchanged,
  no spurious crop.
- Single-pixel speckle below the glyph row: with default
  `ink_run_min_length_px=2`, speckle is rejected; bottom snaps to
  the real glyph row. With `ink_run_min_length_px=1`, speckle wins
  (regression guard for the parameter).
- Pixel-space and normalized bbox both supported (mirror existing
  `_normalized` / `_pixel` parametrizations in the file).
- Error path: `image=None` raises (existing `test_crop_bottom_none_image_error`
  pattern at line 597).

No new image fixtures needed; tiny synthetic numpy arrays drawn
inline (same as existing `test_crop_top_and_bottom` at
`tests/ocr/test_word.py:557`).

#### `Word.crop_bottom_to_baseline` — needs a real cropped image

Lives in `pd-book-tools/tests/ocr/test_word.py` next to
`test_refine_*` (lines 234–356) and `test_crop_top_and_bottom`
(line 557). Existing fixtures (`pixel_bbox`, `hello_word`,
`refine_bbox_case`) and the `tests/ocr-test-image.png` provide a
foundation; nothing else has to be added.

For glyph-level coverage we generate small synthetic images inline
with PIL — same pattern as the existing word/bbox tests (no real book
scans checked in, no font files beyond what is already used). A
helper `_render_word(text, baseline_y, descender_depth, ...)` in the
test module draws glyphs onto a fixed-size grayscale array with known
geometry. This keeps tests deterministic and Pillow-version
sensitivity bounded (see §12.5).

Cases:

- "the" (no descenders): bottom crops tight to ascender baseline +
  `safety_pad_px`; descender zone removed.
- "page" (descenders on `g` and `p`): bottom remains at
  `baseline + descender_allowance`; descender ink preserved within
  ±1 px.
- "j" — single-character word that is itself a descender. Per safety
  rule 5.4, skipped. Asserts the skip path, including the per-skip-
  reason histogram entry.
- "Quito" — capital `Q` descender if `Q` is in
  `DESCENDER_CHARS`. Asserts `Q` is treated as descender-bearing
  (locks in the §2.1 broadening from Q6 / decision-needed item 4).
- "Hello," — descender from punctuation `,`. Asserts that
  punctuation in `DESCENDER_CHARS` causes the word as a whole to
  be treated as descender-bearing.
- Non-Latin text (e.g. `"Ωμέγα"`, `"日本"`): per safety rule 5.7,
  skip with `non-latin` reason.
- Empty GT, non-empty OCR: classification falls back to OCR text
  (§2.3 case 1).
- Empty GT and OCR: skip with `no-text` reason (§2.3 case 2).
- **GT-says-no-descender, ink-extends-down case.** Render "the"
  with a small bleed-through artifact below the baseline. Whichever
  side §14 / Q-new-1 lands on, the test enforces it: the proposal
  here is `ink wins` — i.e. the no-descender crop snaps to the ink
  row, not to baseline + safety_pad. This decision is forced by this
  spec and added to §14 as a new decision-needed item.
- Idempotence: running twice is a fixed point on the second call
  (regression guard).
- Monotonicity: the new bottom is `<=` the old bottom (in image-y
  terms — bottom moves up or stays put, never down).

#### `Block.crop_word_bottoms_to_baseline` — per-line baseline shared across words

Lives in `pd-book-tools/tests/ocr/test_block.py`. Cases:

- Mixed-descender line: 5 words, 2 descender-bearing, 3 not. Assert
  the *same* `baseline_y` is used for all 5 words (verifiable by
  the per-word target_y values under known x-height).
- All-no-descender line ("THE END"): bottom crops to lowest ink row
  on every word; per-line baseline still computed but functionally
  equals the lowest ink.
- All-descender line (rare; e.g. "page jury gypsy"): every word
  keeps `descender_allowance`. No word's bbox shrinks past
  `baseline + allowance`.
- Tilted line (intentionally rotate the synthetic image ~2°):
  per-line baseline is the average; assert the shared baseline is
  within tolerance of mean glyph bottom. Avoid testing exact pixel
  parity here — too fragile; assert the *shared baseline* property
  instead.
- Line below `min_words_for_baseline=3`: falls back to per-word ink
  scan (§7). Assert per-word path is taken.
- Returns the per-skip-reason histogram from §9 with correct counts.

#### `Page.crop_word_bottoms_to_baseline` — happy path + skip rules

Lives in `pd-book-tools/tests/ocr/test_page.py` (or
`test_page_more_coverage.py`, mirroring existing
`test_refine_bounding_boxes_*` patterns). Cases:

- Happy path: a 3-line synthetic page. Each line gets its own
  baseline. Word counts in the histogram add up to total words
  (cropped, skipped, and unchanged sum to total).
- Page with `cv2_numpy_page_image=None`: returns 0 cropped, all
  words skipped with `no-image` reason (mirror existing refine
  behaviour).
- Page with one empty block: empty block contributes nothing;
  no error.
- Single-character word skip rule (§5.4): asserted at page scope so
  the rule is exercised through the public entry point too.

#### Property / regression tests

- **Idempotence**: running the page-level method twice returns
  histogram with `cropped == 0` on the second call (modulo
  `min_crop_px` rounding).
- **Monotonicity**: for every word, `new_bbox.bottom <= old_bbox.bottom`.
  Asserted across all unit tests via a shared helper.
- **Non-Latin guard**: a synthetic page whose GT text is entirely
  Cyrillic or CJK leaves all bboxes unchanged (defends against §13
  decision on Q2).

### 11.2 pd-ocr-labeler side

#### Unit tests for `BboxOperations.crop_bottoms_*`

Lives in `pd-ocr-labeler/tests/pd_ocr_labeler/operations/ocr/test_bbox_operations.py`
(file already exists; new test classes alongside existing `refine_*`
tests). Cases per scope (`words`, `lines`, `paragraphs`):

- Delegates to the pd-book-tools entry point with the right scope
  arguments. Mock the pd-book-tools call to keep these tests off the
  image pipeline (`mocker.patch(
  "pd_book_tools.ocr.page.Page.crop_word_bottoms_to_baseline")`).
- Skips `WORD_LABEL_VALIDATED` words: build a fake page with one
  validated word, assert it's not in the list passed to the
  pd-book-tools call.
- Returns the operation result shape expected by
  `word_match_actions._handle_crop_bottoms_*` (count + histogram).
- No-op when selection is empty.

#### Unit tests for `PageOperations.crop_bottoms_all_words`

Lives in `pd-ocr-labeler/tests/pd_ocr_labeler/operations/page_operations/`
(directory already exists alongside `bbox_operations`). Cases:

- Delegates to pd-book-tools page-level method. Mocked.
- Returns `False` (or analogous "no-op") when
  `page.cv2_numpy_page_image is None` — mirrors existing
  `refine_all_bboxes` behaviour.

#### Playwright E2E tests

Lives in `pd-ocr-labeler/tests/browser/`. New file:
`test_toolbar_crop_bottoms.py`, modeled on
`test_toolbar_word_actions.py` (which already covers
`word-refine-bboxes-button` at lines 199–209) and the
paragraph/line/page equivalents in the same directory. Test IDs
introduced by §3:

- `page-crop-bottoms-button`
- `paragraph-crop-bottoms-button`
- `line-crop-bottoms-button`
- `word-crop-bottoms-button`

Cases (one per scope, same shape as the existing refine tests):

- Button is present and visible after the toolbar renders.
- Button is enabled when a word/line/paragraph is selected (per
  scope), disabled otherwise — matching existing scope-grid
  behaviour.
- Click triggers a success notification (
  `_wait_for_notification(page)` helper exists in
  `tests/browser/helpers.py`).
- Validated words are not modified: pre-validate one word in the
  fixture project (the browser fixture project at
  `tests/browser/fixtures/browser-test-project` already has multiple
  pages; pick one), click `page-crop-bottoms-button`, assert the
  validated word's bbox is unchanged in the saved JSON.
- Re-applying the action is a visible no-op (notification still
  fires; no second-click crash).

The fixture project at
`tests/browser/fixtures/browser-test-project` is the existing
Playwright fixture; reuse rather than introduce a new one. The
single-page `saved-pages` payload is sufficient to exercise all four
scope buttons. No new fixture downloads or extra ML model loading.

#### Snapshot / golden tests

Optional. The labeler does not currently have a visual-regression
harness (no Playwright `expect(page).toHaveScreenshot()` use, no
checked-in baseline images). Skipping for v1; revisit only if
Playwright snapshots become standard across the rest of the suite.

### 11.3 Test data

- **pd-book-tools existing fixtures.**
  - `pd-book-tools/tests/ocr-test-image.png` — used by the existing
    refine and crop tests (`test_word.py:557`,
    `test_bounding_box.py:1022+`). Reuse for the
    happy-path cases of `BoundingBox.crop_bottom_to_y` where a real
    photographic background is preferable to inline synthetic.
  - `pd-book-tools/tests/fixtures/layout_regression/` — book-page
    layout fixtures with `.json` + `.png` pairs. Heavyweight (whole
    pages); not needed for the unit tests proposed here. Keep them
    out of v1 to avoid coupling crop-bottom tests to layout-detector
    changes.
  - For glyph-level descender / no-descender coverage, generate
    inline with PIL inside the test module. Same pattern as existing
    word tests; no font files beyond OS defaults.
- **pd-ocr-labeler existing fixtures.**
  - `tests/browser/fixtures/browser-test-project` — used by every
    existing toolbar Playwright test. Reuse directly; do not
    introduce a new project.
  - `tests/test-data/pgdp-projects/` — pre-saved real OCR output
    used by integration tests. Not needed here (image-aware tests
    live in pd-book-tools).

#### Specific test-case word list

For glyph-coverage in `Word.crop_bottom_to_baseline` /
`Block.crop_word_bottoms_to_baseline`:

- `"the"` — no descenders; tight crop expected.
- `"page"` — descenders on `g` and `p`; descender preserved.
- `"jury"` — descenders on `j` and `y`; verifies `y` is in the
  broadened set (Q6).
- `"j"` — descender-only single-char skip case (§5.4).
- `"Quito"` — capital `Q` descender; verifies uppercase in set.
- `"Hello,"` — punctuation descender; verifies punctuation in set.
- `"page,"` — both glyph and punctuation descenders; redundant for
  classification but exercises the union.
- `"THE END"` — all-uppercase, no descenders; per-line baseline
  collapses to lowest ink row.

### 11.4 What we are NOT testing in v1

- **Real book scans across the corpus.** Manual visual review on a
  handful of pages, not CI. The corpus test set is too large to
  include in the test suite and any single-page check in CI would
  be more cargo cult than useful signal.
- **Performance / benchmarks.** Page-scope timing on 500-word pages
  should be eyeballed once during implementation review and
  recorded in the implementation PR description, but it is not a
  CI gate. No `pytest-benchmark` dependency added.
- **Cross-version Pillow rendering parity.** We pin the *minimum*
  Pillow but do not pixel-diff across versions; the synthetic
  fixtures are tolerant by ±1 px (see §12.5).
- **Real-OCR confidence interactions.** The §2.3 fallback policy
  ("OCR text mostly trustworthy, skip if bbox is suspiciously
  short") is exercised at the unit level only; we do not run real
  OCR in tests.

## 12. CI integration plan

### 12.1 Where the tests run today

- **pd-book-tools.** `.github/workflows/ci.yml` is a single job on
  `ubuntu-latest`, no Python matrix, no GPU. It calls `make install`
  then `make ci`, and `make ci` is `install → pre-commit-check →
  test → build → layout-fork-info`. `make test` is
  `uv run pytest -n auto -v -ra`. Coverage exists as a target
  (`make coverage`) but is not run in CI; `fail_under = 0` in
  `pyproject.toml`.
- **pd-ocr-labeler.** `.github/workflows/ci.yml` is a single job on
  `ubuntu-latest`. It checks out the labeler into `pd_ocr_labeler/`,
  *also* checks out `ConcaveTrillion/pd-book-tools` into
  `pd-book-tools/` (sibling directory), then runs `make install` and
  `make ci`. Note: the sibling checkout is currently dead code from
  CI's point of view — `tool.uv.sources` in `pyproject.toml` pins
  `pd-book-tools` to a specific git tag (`v0.9.0` at time of
  writing), so the resolver fetches the tagged commit, not the
  sibling. The sibling checkout step is either a holdover or
  preparation for a future editable-install path; either way it
  does *not* affect what version of pd-book-tools the tests run
  against. (Flagged as new open question Q-new-2.)
  `make ci` runs `setup → pre-commit-check → test → build`.
  `make test` is `uv run pytest -n auto -v -ra`. **`make ci` does
  NOT include `make test-browser`** — the Playwright suite is
  currently developer-local and not gated in CI. (Flagged as
  Q-new-3.)

### 12.2 What needs to change

- **pd-book-tools.** New unit tests slot directly into the existing
  pytest run via `make test`. No new dependencies, no new image
  utilities — Pillow is already pulled in transitively (used for the
  existing refine / crop tests). Confirm only that the synthetic
  glyph helper does not introduce a font-file dependency: stick to
  PIL `ImageDraw.text` with the bundled default font, or with the
  font already used elsewhere in the suite (none currently — default
  is fine for shape-only assertions). No CI changes; the new test
  files are picked up by `pytest`'s default discovery.
- **pd-ocr-labeler.**
  - Unit tests in `tests/pd_ocr_labeler/operations/` slot into
    `make test`. Mocked away from images, so no new fixtures or
    downloads.
  - Playwright tests: this is the bigger ask. They currently are
    not in CI. Two paths:
    (a) Land the Playwright tests in `make test-browser` only,
        document them in the PR, and leave the CI gating decision
        to a follow-up. v1-friendly.
    (b) Add a separate CI job (or step) that runs `make test-browser`
        with `make setup` (which installs Playwright Chromium).
        Adds ~3–5 min and an extra system-deps install. Cleaner
        but expands CI scope. Recommended: (a) — keep the change
        atomic, then promote in a follow-up PR.
  - Either way: no new fixture downloads; the existing
    `tests/browser/fixtures/browser-test-project` covers the new
    buttons.
- **Cross-repo coupling.** The labeler currently consumes
  pd-book-tools by **git tag pin** (`tool.uv.sources` →
  `tag = "v0.9.0"`). To pick up the new bottom-crop methods:
  1. Land changes in pd-book-tools.
  2. Cut a new tag (e.g. `v0.10.0`).
  3. Run `make upgrade-pd-book-tools` in the labeler (the existing
     target at `Makefile:146` does the bump and `uv sync`).
  4. Land the labeler-side changes pinned to the new tag.

  This is the same shape as every existing labeler change that
  needed a pd-book-tools API addition; no new mechanism. The CI
  workflow already runs `make install` which honours the new pin.
  No editable-install dance; the sibling checkout in
  `.github/workflows/ci.yml:18-21` is unchanged (and remains dead;
  Q-new-2).

### 12.3 Pre-commit / local hooks

Both repos run `ruff-check` and `ruff-format` via pre-commit. New
test files trigger the standard hooks; no new hooks needed. The
labeler's pre-commit also runs `markdownlint-cli2`; this spec
update is the only Markdown change and lints clean (verify with
`make md-lint` post-edit). Nothing custom required for crop-bottom
test files.

### 12.4 Coverage targets

- pd-book-tools: `fail_under = 0` (no gate). Match existing
  module thresholds — i.e. *no new gate*. The new methods will be
  covered well by the unit tests above; we don't add a v1 numeric
  threshold.
- pd-ocr-labeler: same. `fail_under = 0` per
  `pyproject.toml:67`. Revisit thresholds in v2 if/when the
  project introduces a global coverage gate.
- Coverage of the new code path is exercised end-to-end by the
  Playwright button tests, but Playwright tests do not contribute
  to coverage runs (they spawn a subprocess). Acceptable; the unit
  tests carry the coverage weight.

### 12.5 CI failure modes to anticipate

- **Playwright flake on the new buttons.** Mitigation: copy the
  exact existing `_setup → _select_word → click → _wait_for_notification`
  sequence from `test_toolbar_word_actions.py:199`. No bespoke
  waits. If a particular scope's button takes longer to settle,
  use `expect(locator).to_be_enabled()` before click, not a manual
  `time.sleep`.
- **Image-rendering differences across Pillow versions.** Synthetic
  glyph fixtures rendered with `PIL.ImageDraw` can shift by ±1 px
  between Pillow major versions (anti-aliasing changes,
  font-fallback changes). Mitigation:
  - Tests assert *relative* movement of the bbox bottom, not
    absolute pixel coordinates. e.g. "bottom moved up by at least
    `expected_descender_zone_px`", not "bottom == 47".
  - Where exact comparison is needed (the
    `crop_bottom_to_y` snap-to-ink case), use deterministic
    hand-drawn numpy arrays (`np.zeros(...)` plus explicit pixel
    sets) rather than `ImageDraw.text` — cuts the dependency on
    Pillow's font rendering entirely.
  - Pillow stays unpinned (we follow the rest of the repo); we
    rely on the assertion shape, not version pinning.
- **Otsu threshold sensitivity.** Otsu is histogram-dependent; a
  fixture with too few non-background pixels produces an unstable
  threshold. Mitigation: in tests where threshold determinism
  matters (e.g. the `ink_run_min_length_px` speckle-rejection
  test), construct binary-clean inputs (only 0 and 255) so Otsu
  is forced into a known split. Don't rely on Otsu on grey
  fixtures.
- **Per-line baseline jitter on tilted synthetic input.** Don't
  rotate fixtures inside tests — keep synthetic glyphs axis-aligned
  unless specifically testing tilt. The one tilt test asserts a
  *property* (shared baseline across words), not exact pixel
  positions, per §11.1.
- **Subprocess port collisions.** The Playwright fixture
  (`tests/browser/conftest.py`) already picks a free port per
  worker; the new tests inherit the existing fixture. No change.

## 13. Open questions

These need user input before implementation starts.

- **Q1.** Do any of the project's target corpora use old-style
  figures (`3 4 5 7 9` descending below baseline)? If yes, default
  `oldstyle_figures_descend = True` is safer for those projects;
  if you'd rather keep the default off and toggle per-project,
  where should that toggle live (project metadata? operator
  prompt at run-start, like long-s in the pre-pass driver)?
- **Q2.** Latin-script gating in section 5.7: where exactly does the
  cutoff live? Just "in U+0000–U+024F" is too coarse (excludes
  Latin Extended Additional, includes IPA). Suggest reading the
  same project-level "languages present" hint that the OCR
  configuration already implies, but that hint is not currently
  exposed as such — confirm the right source.
- **Q3.** Per-line baseline confidence threshold: if
  `Word.estimate_baseline_from_image` reports low confidence on
  most words in a line (e.g. heavily warped scan), should we
  abort the line entirely, or fall back to per-word ink scan?
  Spec leans fall-back, but you may prefer hard-skip + log so it
  surfaces problem pages.
- **Q4.** Does the labeler want to surface skipped-word reasons
  visibly (toast detail or dedicated tooltip) or just in the
  in-process logger?
- **Q5.** Icon choice. `vertical_align_bottom` reads best to me
  (Material icon, common). Confirm the icon set in use covers it,
  or pick another from `pd_ocr_labeler/views/shared/button_styles.py`.
- **Q6.** Is the descender character set in section 2.1 the right
  shape, or do you want me to align it strictly with the existing
  `pd_book_tools/ocr/word.py` set (`p g j q Q`) for consistency
  even though that misses `y`, `J`, and punctuation? Strong
  recommendation is to broaden, but flagging because it's a
  cross-repo behaviour change.
- **Q7.** `min_crop_px` default of 2: is 2 px the right floor, or
  do you want it more aggressive (1 px) or more conservative (3–4
  px)? Affects how often the tool is a no-op.
- **Q8.** Pre-pass driver inclusion: do you want this tool in the
  driver's whitelist immediately (section 3 recommends not), or
  is "human-only in v1, revisit in v2" acceptable?
- **Q9.** Should the new pd-book-tools functions live next to
  `refine_bbox` on `Word` and on the existing `refine_word_bboxes`
  on `Block` (proposed location), or under a new `bbox_crop`
  module to keep the heuristic-heavy code separate from the
  geometric primitives? Current proposal puts them on the same
  classes for symmetry with refine.
- **Q-new-1.** When GT text says "no descender" but ink visibly
  extends below the baseline (bleed-through, dirt, italic tail
  from neighbour, mis-spaced descender of the line below),
  **which signal wins** for the bottom edge? Spec §11.1 proposes
  `ink wins` (snap to the lowest ink row, ignoring the GT-driven
  baseline target). Surfaced by writing the Word-level test
  cases — needs a decision before tests can be locked in.
  Promoted to §14 as decision-needed item 6.
- **Q-new-2.** The labeler CI checks out `pd-book-tools` as a
  sibling directory but does not actually use it — `tool.uv.sources`
  pins to a git tag, so the resolver fetches the tag, not the
  sibling. Is the sibling checkout (a) dead code, (b) preparation
  for a future editable-install path, or (c) expected to be wired
  up *as part of this work* so labeler tests pick up unreleased
  pd-book-tools changes? Current spec assumes (a) — release-by-tag
  is fine — but if (c) is preferred, the labeler workflow needs a
  `tool.uv.sources` override for CI.
- **Q-new-3.** The Playwright suite (`make test-browser`) is not
  currently gated in CI. The new bottom-crop buttons will have
  Playwright tests; do we (a) leave them developer-local for v1
  and gate in a follow-up PR, or (b) wire `make test-browser`
  into CI in this same change? §12.2 recommends (a) to keep the
  scope atomic.
- **Q-new-4.** Coverage gating: spec §12.4 keeps `fail_under = 0`
  (the existing posture). Confirm we are not adding a per-module
  threshold for the new pd-book-tools / labeler code, even
  informally. If we *are* expected to set one, what is the target?

## 14. Decisions requested

The minimum set of decisions needed to start coding:

1. (Section 3) **Separate button vs folded into Refine Bboxes** —
   spec recommends separate. Confirm or push back.
2. (Section 9) **pd-book-tools vs labeler split** — spec recommends
   the split as described. Confirm or push back.
3. (Section 8) **Pre-pass driver inclusion in v1** — spec recommends
   no. Confirm or push back.
4. (Q6) **Descender character set** — spec recommends broadening.
   Confirm scope.
5. (Q1) **Old-style figures default** — pick a default, or commit to
   the per-project toggle pattern.
6. (Q-new-1) **Ink-vs-GT priority** for the no-descender + ink-below
   case. Spec recommends `ink wins`. Forced earlier than originally
   planned because the Word-level test cases in §11.1 cannot be
   written without it.

Everything else in section 13 can be answered during implementation
review.
