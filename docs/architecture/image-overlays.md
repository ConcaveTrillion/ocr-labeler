---
kind: architecture
status: active
owner: repository maintainers
created: 2026-07-14
last_verified: 2026-07-14
---

# Image overlays

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing the page viewport, overlay layers, or selection modes.
- **Search terms:** unified viewport, SVG overlays, paragraph line word layers.

`ImageTabs` renders one interactive page viewport with independently controlled
paragraph, line, and word SVG layers. Selection mode changes which geometry is
interactive. The implementation kept the historical `ImageTabs` surface and
some legacy tab terminology for compatibility instead of renaming the component
around the unified viewport.

## Evidence

- Code: `pd_ocr_labeler/views/projects/pages/image_tabs.py`
- Unit tests: `tests/pd_ocr_labeler/views/projects/pages/test_image_tabs.py`
- Browser tests: `tests/browser/test_image_tabs.py`
- Verified: 2026-07-14 during the docgraph migration
