"""Chrome browser session manager supporting native debug profile and CDP."""

import logging
import os
import socket
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Playwright

from crowdgen_automation.instances import InstanceConfig

logger = logging.getLogger(__name__)


def is_cdp_available(port: int = 9222) -> bool:
    """Check if Chrome remote debugging port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False


def get_chrome_debug_dir() -> Path:
    """Return persistent user data path for dedicated Chrome debug session."""
    base = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path.home())
    p = Path(base) / ".chrome-debug"
    p.mkdir(parents=True, exist_ok=True)
    return p


def acquire_browser_session(
    p: Playwright, inst: InstanceConfig
) -> tuple[BrowserContext, Page, bool]:
    """Connect to existing Chrome via CDP or launch with debug profile."""
    if is_cdp_available():
        logger.info("Connecting to active Chrome session via CDP (port 9222)...")
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "annotate" in pg.url or "cloudfront" in pg.url), None)
        return context, page or (context.pages[0] if context.pages else context.new_page()), True

    logger.info("CDP not detected on port 9222. Launching Chrome with debug profile...")
    user_dir = get_chrome_debug_dir()
    for lk in user_dir.glob("Singleton*"):
        try:
            lk.unlink(missing_ok=True)
        except OSError:
            pass
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(user_dir), channel="chrome", headless=inst.headless,
        viewport={"width": 1400, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    return context, context.pages[0] if context.pages else context.new_page(), False
