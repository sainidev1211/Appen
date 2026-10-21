"""Orchestrator for Project Origami / Maven task processing lifecycle."""

import logging
import time

import playwright.sync_api as pw
from tenacity import RetryError

from crowdgen_automation.auth import launch_project
from crowdgen_automation.config import Settings
from crowdgen_automation.tasks.capture import capture_task_image, get_task_context
from crowdgen_automation.tasks.filler import fill_maven_form
from crowdgen_automation.tasks.skipper import skip_task
from crowdgen_automation.tasks.submit import submit_task
from crowdgen_automation.tasks.unit_loader import wait_for_new_unit
from crowdgen_automation.tasks.validator import click_validate
from crowdgen_automation.tasks.vision_solver import generate_captions

logger = logging.getLogger(__name__)

def process_single_task(page: pw.Page, cfg: Settings, auto_submit: bool) -> bool:
    start_time, context = time.monotonic(), get_task_context(page)
    _, img_ref = capture_task_image(context)
    error_feedback: str | None = None
    for attempt in range(1, 3):
        logger.info("Generating captions (attempt %d/2)...", attempt)
        captions = generate_captions(img_ref, cfg, error_feedback=error_feedback)
        if captions.get("is_dense") in (True, "true"):
            logger.info("Dense document detected. Skipping task as requested...")
            return skip_task(context, page)
        fill_maven_form(context, captions)
        if captions.get("unusable_quality") in (True, "true"):
            return submit_task(context, start_time, auto_submit, cfg.target_remaining_sec, page=page)
        passed, error_feedback = click_validate(context)
        if passed and submit_task(context, start_time, auto_submit, cfg.target_remaining_sec, page=page):
            return True
        logger.warning("Attempt %d failed (error: %s).", attempt, error_feedback)
    return skip_task(context, page)

def process_maven_tasks(page: pw.Page, cfg: Settings, auto_submit: bool = True) -> None:
    launch_project(page)
    logger.info("Starting continuous Maven task loop (max: %d)...", cfg.max_tasks)
    curr_unit = ""
    for task_idx in range(1, cfg.max_tasks + 1):
        logger.info("=== Processing Task %d / %d ===", task_idx, cfg.max_tasks)
        if "/annotate/" not in page.url:
            launch_project(page)
        curr_unit = wait_for_new_unit(page, curr_unit)
        try:
            ok = process_single_task(page, cfg, auto_submit=auto_submit)
        except (pw.Error, RetryError, TimeoutError, ValueError, RuntimeError, OSError) as exc:
            err = exc.last_attempt.exception() if isinstance(exc, RetryError) and exc.last_attempt else exc
            logger.warning("Task error: %s", err)
            ok = False
        if not ok:
            page.reload()
            if not auto_submit:
                break
        page.wait_for_timeout(2000)
