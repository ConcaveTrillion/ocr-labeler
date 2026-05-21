# CLAUDE — pd-ocr-labeler

NiceGUI web app for reviewing and correcting OCR output. Displays page images
with overlays; lets users edit words/lines/paragraphs, tag styles, and save
corrections as ground truth. Depends on `pd-book-tools` for OCR and
page-model primitives.

## Commands

| target | does |
| --- | --- |
| `make setup AI=1` | dev venv + pre-commit + Playwright |
| `make install` | `uv tool install` (puts `pd-ocr-labeler-ui` on PATH) |
| `make test AI=1` | `uv run pytest -n auto` |
| `make test-k K='pat' AI=1` | targeted pytest with `-n auto` |
| `make test-single TEST='...' AI=1` | single test file/function |
| `make test-browser AI=1` | Playwright browser regression tests |
| `make lint AI=1` / `make lint-fix AI=1` | ruff + markdownlint (with --fix) |
| `make format AI=1` | ruff format |
| `make build AI=1` | build wheel |
| `make run` | start the app |
| `make ci AI=1` | format + lint + test |
| `make coverage AI=1` | coverage report |
| `make clean-cache` / `make clean-logs` | clear page-image cache / runtime logs |

`AI=1` captures verbose output to `.ci-ai.log`; stdout shows `✅` on pass or
filtered failure sections on error. Remove `AI=1` only if you need full verbose
output for debugging.

Always include `-n auto` on pytest invocations.

## Rules

- Always run `make ci AI=1` before committing.
- Make targets first; fall back to `uv run …` only when no target exists.
- Never `python -m pytest` / `python3 -m pytest`. Always `uv run pytest -n auto`
  or `make test` (include `-n auto`). Bare `python`/`python3`/`.venv/bin/python`
  miss the venv.
- NiceGUI async: use `background_tasks.create(…)` for background work and
  `run.io_bound(…)` for blocking I/O. Never `asyncio.create_task`,
  `loop.run_in_executor`, or `asyncio.to_thread` in app code.
- Do not silently swallow recoverable exceptions in UI/navigation flows.
  Log with context and surface a user-visible notification when behavior
  degrades but the app can continue.
- `pd-book-tools` is pinned in `pyproject.toml`; use a `uv.toml` (gitignored)
  with `[tool.uv.sources]` override for local-dev against a sibling checkout —
  see `DEVELOPMENT.md`.
- Run `make lint` after editing any Markdown under `docs/`.

## Runtime logs

Per-session log files: `session_<YYYYMMDD>_<HHMMSS>_<pid>.log` under the
OS-aware app data root (`PersistencePathsOperations.get_logs_root()`).

| OS      | Default log directory                                                               |
| ------- | ----------------------------------------------------------------------------------- |
| Linux   | `$XDG_DATA_HOME/pd-ocr-labeler/logs` (default `~/.local/share/pd-ocr-labeler/logs`) |
| macOS   | `~/Library/Application Support/pd-ocr-labeler/logs`                                 |
| Windows | `%APPDATA%/pd-ocr-labeler/logs`                                                     |

Dev container: `/home/vscode/.local/share/pd-ocr-labeler/logs/`. Most recent
session = latest mtime (`ls -lat`).

Other runtime paths (same `get_*_root()` helpers):

- Page image cache: `$XDG_CACHE_HOME/pd-ocr-labeler/page-images`
- Saved labeled projects: `<data root>/pd-ocr-labeler/labeled-projects`

## Sibling repos

- `../pd-book-tools/` — upstream dependency.

## GH issues

Cross-cut work tasks are tracked as GH issues in
**`ConcaveTrillion/ocr-container-meta`** (not in this repo's own tracker).
Plans under `docs/plans/` in the workspace root are synced there
via `/decompose-spec --sync`. Milestone naming: `spec: <plan-basename> (#N)`.

When shipping a plan task:

- Before starting: `gh issue view <N> --repo ConcaveTrillion/ocr-container-meta`
- After completing: `gh issue close <N> --repo ConcaveTrillion/ocr-container-meta`
- List open tasks:
  `gh issue list --repo ConcaveTrillion/ocr-container-meta --milestone "spec: <name> (#N)" --state open`

## docs/ folder

This repo follows the workspace docs/ template — see [`docs/README.md`](docs/README.md). Active
folders: `architecture/`, `decisions/`, `plans/`, `process/`, `research/`,
`runbooks/`, `specs/`, `templates/`, `usage/`, plus parallel `archive/`
subfolders.

**Superpowers redirect.** When a superpowers skill (e.g. `brainstorming`,
`writing-plans`) instructs you to save to `docs/superpowers/specs/<file>.md`
or `docs/superpowers/plans/<file>.md`, save to `docs/specs/<file>.md` or
`docs/plans/<file>.md` instead. There is no `docs/superpowers/` subdirectory
in this repo.

<!-- workspace-process:start -->

## Before coding

These steps are workspace defaults for any coding task. **User-level settings
override them** — a user's own `~/.claude/CLAUDE.md`, `settings.json`, or a
direct instruction in the conversation takes precedence and may waive or
change any step below.

### Working principles

- **Use skills.** Invoke the relevant superpowers skill before starting —
  process skills first (`brainstorming`, `systematic-debugging`,
  `writing-plans`, `test-driven-development`), then implementation skills.
  If a skill applies, using it is not optional.
- **Delegate by default.** Dispatch subagents for non-trivial work: per-repo
  agents for repo changes, `Explore` for code searches. This keeps large tool
  output out of the parent context.
- **Parallelize.** Run independent tasks as concurrent subagents — multiple
  agent calls in a single message. Set `model: sonnet` on implementers and
  reviewers.

### Steps

1. **Check the working tree.** `git status --short`. Surface or resolve stray
   uncommitted work before starting — don't build on it.
2. **Read repo guidance.** This repo's `CLAUDE.md` and `CONVENTIONS.md` for
   repo-specific rules.
3. **Consult `docs/` for authoritative context** (whichever folders exist):
   `plans/` (the work plan), `specs/` (design specs — follow any `Spec:`
   pointer from the issue), `research/` (prior investigations), `decisions/`
   (ADRs / constraints), `architecture/` (shipped design).
4. **Check live issue status.** `gh issue view <N> --repo <owner/repo>` —
   confirm it isn't already closed; note its milestone.
5. **Check for in-flight work.** Open PRs and existing branches touching the
   same area, to avoid colliding with work-in-progress.
6. **Consult agent memory.** `.claude/agent-memory/<repo>/feedback_*.md` for
   corrections not yet promoted to `CONVENTIONS.md`.
7. **Locate code with `Explore` first.** Use an `Explore` subagent to find
   relevant files before broad `Read`/grep.
8. **Isolate in a worktree.** Never work directly in the interactive checkout
   at `/workspaces/ocr-container/<repo>/`. Use the `using-git-worktrees` skill
   to set up an isolated worktree. When delegating to a full-power
   implementation agent, pass `isolation: "worktree"` on the `Agent` call
   (skip for `-docs` agents and the `driver` agent). When an agent returns a
   worktree path + branch, use the `finishing-a-development-branch` skill to
   decide how to integrate.
9. **TDD.** Write the failing test first where the plan calls for it.
10. **Verify before committing.** Focused verification plus `make ci`.
11. **Commit locally; do not push** without explicit say-so.

<!-- workspace-process:end -->
