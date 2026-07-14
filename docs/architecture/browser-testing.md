---
kind: architecture
status: active
owner: repository maintainers
created: 2026-07-14
last_verified: 2026-07-14
---

# Browser testing

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing Playwright fixtures, UI selectors, or async navigation.
- **Search terms:** Playwright, browser helpers, loading synchronization, testid.

Browser tests load projects through reader-visible controls and synchronize on
enabled navigation before interacting with page content. Stable `data-testid`
attributes are preferred for application controls. Framework-owned custom
elements require public host properties or rendered source attributes; tests
must not assume that a zero-sized host means its resource failed to load.

Distinct editing operations retain direct browser coverage. Shared helpers may
centralize selection and loading behavior, but they must not hide the operation
under test.

## Evidence

- Fixtures and helpers: `tests/browser/conftest.py`, `tests/browser/helpers.py`
- Browser suite: `tests/browser/`
- Verified: 2026-07-14 during the docgraph migration
