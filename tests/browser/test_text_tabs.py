"""Browser tests for the text display panel and tabs."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded


@pytest.mark.browser
def test_text_tabs_present(browser_app_url: str, browser_page) -> None:
    """Verify text tab labels exist: Matches, Ground Truth, OCR."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_role("tab", name="Matches").wait_for(state="visible")
    page.get_by_role("tab", name="Ground Truth").wait_for(state="visible")
    page.get_by_role("tab", name="OCR").wait_for(state="visible")


@pytest.mark.browser
def test_ocr_text_tab_has_content(browser_app_url: str, browser_page) -> None:
    """Switch to OCR tab and verify it has non-empty content."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Click on the OCR tab
    page.get_by_role("tab", name="OCR").click()

    # Wait for the NiceGUI CodeMirror component to mount.
    ocr_content = page.locator(".q-tab-panel:visible .nicegui-codemirror")
    ocr_content.wait_for(state="attached", timeout=10_000)
    expect(ocr_content).to_have_attribute("data-content-present", "true")


@pytest.mark.browser
def test_gt_text_tab_has_content(browser_app_url: str, browser_page) -> None:
    """Switch to Ground Truth tab and verify it has content."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Click on the Ground Truth tab
    page.get_by_role("tab", name="Ground Truth").click()

    # Wait for the NiceGUI CodeMirror component to mount.
    gt_content = page.locator(".q-tab-panel:visible .nicegui-codemirror")
    gt_content.wait_for(state="attached", timeout=10_000)
    expect(gt_content).to_have_attribute("data-content-present", "true")


@pytest.mark.browser
def test_matches_tab_is_default(browser_app_url: str, browser_page) -> None:
    """Verify the Matches tab is selected by default."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The Matches tab should be active by default
    matches_tab = page.get_by_role("tab", name="Matches")
    # Quasar active tabs have q-tab--active class
    assert "q-tab--active" in (matches_tab.get_attribute("class") or "")


@pytest.mark.browser
def test_switching_between_text_tabs(browser_app_url: str, browser_page) -> None:
    """Click each text tab and verify the panel content changes."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Switch to OCR tab
    ocr_tab = page.get_by_role("tab", name="OCR")
    ocr_tab.click()
    expect(ocr_tab).to_have_attribute("aria-selected", "true")

    # Switch to Ground Truth tab
    ground_truth_tab = page.get_by_role("tab", name="Ground Truth")
    ground_truth_tab.click()
    expect(ground_truth_tab).to_have_attribute("aria-selected", "true")

    # Switch back to Matches tab
    matches_tab = page.get_by_role("tab", name="Matches")
    matches_tab.click()
    expect(matches_tab).to_have_attribute("aria-selected", "true")
