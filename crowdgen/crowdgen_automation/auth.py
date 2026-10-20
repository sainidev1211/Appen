"""Maven direct authentication and project launch."""

import logging
import re

from playwright.sync_api import Error, Page

from crowdgen_automation.config import Settings

logger = logging.getLogger(__name__)


def wait_for_auth_complete(page: Page, timeout_sec: int = 180) -> bool:
    """Wait for contributor to authenticate or solve captcha if shown."""
    prof = '[data-testid*="profile"], button:has-text("Logout"), a:has-text("Logout"), :text("Abhinav")'
    for _ in range(timeout_sec):
        if "/annotate/" in page.url or page.locator(prof).first.is_visible():
            return True
        page.wait_for_timeout(1000)
    return False


def launch_project(page: Page) -> None:
    """Click Start button on Oberon Captioning card if on Work dashboard."""
    if "/annotate/" in page.url:
        return
    logger.info("Waiting for 'Start' button on Oberon Captioning card...")
    for _ in range(25):
        if "/annotate/" in page.url:
            return
        btn = page.locator('button:has-text("Start"), a:has-text("Start")').first
        if btn.is_visible(timeout=1000) and btn.is_enabled():
            btn.click()
            page.wait_for_load_state("domcontentloaded")
            logger.info("Clicked 'Start'. Waiting 15s for image and task to load...")
            page.wait_for_timeout(15000)
            return
        page.wait_for_timeout(1000)


def login(page: Page, cfg: Settings, email: str = "", password: str = "", target_url: str = "") -> None:
    """Navigate directly to Maven URL and ensure active project is opened."""
    url = target_url or cfg.login_url
    logger.info("Opening Maven direct URL: %s", url)
    try:
        page.goto(url, wait_until="domcontentloaded")
    except Error:
        page.wait_for_timeout(1000)
        page.goto(url, wait_until="domcontentloaded")
    btn = page.get_by_role("button", name=re.compile(r"log in|sign in", re.IGNORECASE)).first
    if (em := page.locator('input[type="email"], input[name="email"]').first).is_visible(timeout=2000):
        em.fill(email)
        if (pwd := page.locator('input[type="password"]').first).is_visible(timeout=1000):
            pwd.fill(password)
        if btn.is_visible(timeout=1000):
            btn.click()
    wait_for_auth_complete(page)
    launch_project(page)
