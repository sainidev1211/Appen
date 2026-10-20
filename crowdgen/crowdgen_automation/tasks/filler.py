"""Humanized input filling for Project Origami / Maven captioning tasks."""

import logging
import time

from playwright.sync_api import FrameLocator, Locator, Page

logger = logging.getLogger(__name__)

DETAILED_SEL = 'textarea[placeholder*="detailed caption" i], [data-testid*="detailed-caption"]'
SHORT_SEL = 'textarea[placeholder*="short caption" i], [data-testid*="short-caption"]'
ANGLE_SEL = 'input[placeholder*="Leave blank if not applicable" i], input[name*="angle" i]'
NO_ISSUE_SEL = 'label:has-text("No (No Issue Identified)"), input[type="radio"][value*="No" i]'
ISSUE_SEL = 'label:has-text("Yes"), input[type="radio"][value*="Yes" i], label:has-text("Issue")'
DENSE_SEL = 'label:has-text("Dense"), input[type="radio"][value*="Dense" i], [data-testid*="dense" i]'


def _fill_text(loc: Locator, text: str, name: str) -> None:
    if not text:
        return
    loc.wait_for(state="visible", timeout=10000)
    loc.scroll_into_view_if_needed()
    loc.click()
    loc.fill("")
    loc.press_sequentially(text, delay=25, timeout=45000)
    logger.info("Filled %s (%d chars).", name, len(text))
    time.sleep(0.5)


def fill_maven_form(context: Page | FrameLocator, captions: dict[str, str]) -> None:
    """Populate setup questions, detailed caption, short caption, and camera angle."""
    if captions.get("is_dense") in (True, "true"):
        if (dense := context.locator(DENSE_SEL).first).is_visible(timeout=3000):
            dense.click()
            logger.info("Tagged task as Dense Text Document.")
        return
    if captions.get("unusable_quality") in (True, "true"):
        if (issue := context.locator(ISSUE_SEL).first).is_visible(timeout=3000):
            issue.click()
            logger.info("Flagged Image Check (unusable quality). Leaving captions empty.")
        return

    no_issue = context.locator(NO_ISSUE_SEL).first
    if no_issue.is_visible(timeout=3000):
        no_issue.click()
        logger.info("Selected 'No (No Issue Identified)'.")

    # Step 3 Order: Write Detailed caption first, then Short caption
    detailed_loc = context.locator(DETAILED_SEL).first
    _fill_text(detailed_loc, captions.get("detailed_caption", "").strip(), "detailed caption")

    short_loc = context.locator(SHORT_SEL).first
    _fill_text(short_loc, captions.get("short_caption", "").strip(), "short caption")

    angle_text = captions.get("camera_angle", "").strip()
    if angle_text:
        angle_loc = context.locator(ANGLE_SEL).first
        if angle_loc.is_visible(timeout=1000):
            _fill_text(angle_loc, angle_text, "camera angle")
