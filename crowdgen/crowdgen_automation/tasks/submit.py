import contextlib
import logging
import random
import time

from playwright.sync_api import Error, FrameLocator, Locator, Page

logger = logging.getLogger(__name__)
JS_TIMER = "() => { const el = Array.from(document.querySelectorAll('*')).reverse().find(e => /REMAINING\\s*\\d+:\\d+/i.test(e.textContent||'')); const m = el ? (el.textContent||'').match(/REMAINING\\s*(\\d+):(\\d+)/i) : null; return m ? parseInt(m[1],10)*60 + parseInt(m[2],10) : null; }"


def get_page_remaining_seconds(page: Page) -> int | None:
    with contextlib.suppress(Error, TypeError, ValueError, RuntimeError):
        val = page.evaluate(JS_TIMER)
        return int(val) if isinstance(val, (int, float)) else None
    return None

def _find_submit_btn(context: Page | FrameLocator, page: Page | None) -> Locator | None:
    for tgt in ([context, page] if page and page != context else [context]):
        for sel in ('button:has-text("Submit")', 'button[type="submit"]', 'input[value="Submit"]'):
            try:
                btn = tgt.locator(sel).first
                btn.scroll_into_view_if_needed(timeout=2000)
                if btn.is_visible():
                    return btn
            except (Error, TimeoutError):
                pass
    return None

def wait_for_target_timer(page: Page | None, start_time: float, target_remaining_sec: int = 0) -> None:
    if target_remaining_sec <= 0:
        return
    while True:
        rem = get_page_remaining_seconds(page) if page else None
        rem = max(0, 300 - int(time.monotonic() - start_time)) if rem is None else rem
        if rem <= target_remaining_sec:
            logger.info("Target reached (%d:%02d remaining). Submitting...", rem // 60, rem % 60)
            break
        logger.info("Timer: %d:%02d remaining (target: %d:%02d)...", rem // 60, rem % 60, target_remaining_sec // 60, target_remaining_sec % 60)
        time.sleep(min(rem - target_remaining_sec, 5))
def submit_task(context: Page | FrameLocator, start_time: float, auto_submit: bool = True, target_remaining_sec: int = 0, page: Page | None = None) -> bool:
    if not auto_submit:
        logger.info("Review mode: Captions filled & validated. Please submit.")
        return True
    if target_remaining_sec > 0:
        target = random.randint(target_remaining_sec - 5, target_remaining_sec + 5)
        wait_for_target_timer(page or (context if isinstance(context, Page) else None), start_time, target)
    if not (sub_btn := _find_submit_btn(context, page)):
        logger.warning("Submit button not found.")
        return False
    logger.info("Waiting 20 seconds before submitting...")
    time.sleep(20)
    sub_btn.click()
    if (conf := (page or context).locator('button:has-text("Yes, submit"), button:has-text("Confirm")').first).is_visible():
        conf.click()
    logger.info("Task submitted successfully!")
    return True

