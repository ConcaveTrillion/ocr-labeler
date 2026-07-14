---
kind: architecture
status: active
owner: repository maintainers
created: 2026-07-14
last_verified: 2026-07-14
---

# Persistence and provenance

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing saved pages, cache lanes, provenance, or session restore.
- **Search terms:** schema 2.1, envelope, atomic write, source lane, provenance.

Saved user pages use `UserPageEnvelope` schema 2.1. The envelope stores source
fingerprints, OCR provenance, and cached-image metadata. Page operations write
atomically, read legacy data, and keep source-specific lanes separate. Session
state stores the last project path and page index.

The implementation differs from the earlier plan: it uses OS-aware application
storage and envelopes rather than a project-local manifest. Native
`pd-book-tools` Page provenance is preferred, with compatibility fallbacks for
older objects.

## Evidence

- Code: `pd_ocr_labeler/models/user_page_persistence.py`
- Code: `pd_ocr_labeler/operations/ocr/page_operations.py`
- Code: `pd_ocr_labeler/operations/persistence/session_state_operations.py`
- Tests: `tests/pd_ocr_labeler/models/test_user_page_persistence.py`
- Tests: `tests/pd_ocr_labeler/operations/persistence/test_save_load_round_trip.py`
- Verified: 2026-07-14 during the docgraph migration
