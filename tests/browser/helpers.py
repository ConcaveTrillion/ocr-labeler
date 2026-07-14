"""Reusable wait and interaction helpers for Playwright browser tests."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def wait_for_app_ready(page: Page, timeout: int = 30_000) -> None:
    """Wait for the NiceGUI app to be fully rendered."""
    page.get_by_text("Project").first.wait_for(state="visible", timeout=timeout)


def wait_for_page_number(page: Page, expected: str, timeout: int = 30_000) -> None:
    """Poll until the page number input shows the expected value."""
    page_input = page.locator('[data-testid="nav-page-input"]')
    expect(page_input).to_have_value(expected, timeout=timeout)


def load_project(page: Page, project_name: str, timeout: int = 60_000) -> None:
    """Load a project through the UI by selecting it and clicking LOAD.

    Args:
        page: Playwright page object.
        project_name: Name of the project to select from the dropdown.
        timeout: Maximum time to wait for loading in milliseconds.
    """
    # Click the Quasar select dropdown to open it
    select = page.locator(".q-select").first
    select.click()

    # Wait for dropdown popup and click the target project option
    page.locator(".q-menu .q-item").get_by_text(project_name).click()

    # Click the LOAD button (testid'd in ProjectLoadControls)
    page.locator('[data-testid="load-project-button"]').click()

    # Wait for loading overlay to appear then disappear
    loading_overlay = page.locator("[data-nicegui-mark='project-loading-overlay']")
    loading_overlay.wait_for(state="hidden", timeout=timeout)

    # Wait for navigation controls to appear (indicates project loaded)
    page.locator('[data-testid="nav-next-button"]').wait_for(state="visible", timeout=timeout)
    wait_for_page_loaded(page, expected_page="1", timeout=timeout)


def wait_for_page_loaded(
    page: Page,
    expected_page: str | None = None,
    previous_image_src: str | None = None,
    timeout: int = 60_000,
) -> None:
    """Wait for page content to finish loading after navigation."""
    page.locator('[data-testid="nav-page-input"]').wait_for(state="visible", timeout=timeout)
    expect(page.locator('[data-testid="nav-page-input"]')).to_be_enabled(timeout=timeout)
    page_input = page.locator('[data-testid="nav-page-input"]')
    if expected_page is not None:
        expect(page_input).to_have_value(expected_page, timeout=timeout)
    viewport = page.locator(".ocr-viewport-img").first
    expect(viewport).to_have_attribute("src", re.compile(r"^/.+"), timeout=timeout)
    if previous_image_src is not None:
        expect(viewport).not_to_have_attribute("src", previous_image_src, timeout=timeout)


def navigate_to_page(page: Page, page_number: int, timeout: int = 60_000) -> None:
    """Navigate to a specific page number using the Go To input.

    Args:
        page: Playwright page object.
        page_number: 1-based page number to navigate to.
        timeout: Maximum time to wait for navigation.
    """
    previous_image_src = page.locator(".ocr-viewport-img").first.get_attribute("src")

    # Find and fill the page number input
    page_input = page.locator('[data-testid="nav-page-input"]')
    page_input.fill(str(page_number))

    # Click the Go To button
    page.locator('[data-testid="nav-goto-button"]').click()

    # Wait for navigation to complete
    wait_for_page_loaded(
        page,
        expected_page=str(page_number),
        previous_image_src=previous_image_src,
        timeout=timeout,
    )


def get_current_page_number(page: Page) -> str:
    """Read the current page number from the navigation input."""
    return page.locator('[data-testid="nav-page-input"]').input_value()


def get_page_total_text(page: Page) -> str:
    """Read the total page count text (e.g., '/ 3')."""
    # The total is displayed as a label like "/ 3" next to the page input
    total_label = page.locator('[data-testid="nav-page-total-label"]')
    return total_label.text_content() or ""
