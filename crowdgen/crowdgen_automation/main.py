"""Parallel multi-instance orchestrator for CrowdGen Maven automation."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from playwright.sync_api import Error, sync_playwright

from crowdgen_automation.auth import login
from crowdgen_automation.browser import acquire_browser_session
from crowdgen_automation.instances import InstanceConfig, load_instances
from crowdgen_automation.keep_awake import keep_awake
from crowdgen_automation.tasks.coordinator import process_maven_tasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_instance(inst: InstanceConfig) -> None:
    """Execute complete workflow for single CrowdGen instance."""
    cfg = inst.to_settings()
    with sync_playwright() as p:
        try:
            context, page, is_cdp = acquire_browser_session(p, inst)
        except Error as exc:
            if "ProcessSingleton" in str(exc):
                logger.error(
                    "Chrome is already running! Run 'start_chrome_debug.bat' or close Chrome first."
                )
            raise
        try:
            if "/annotate/" not in page.url:
                login(page, cfg, email=inst.email, password=inst.password, target_url=inst.task_url)
            process_maven_tasks(page, cfg, auto_submit=inst.auto_submit)
        finally:
            if not is_cdp:
                context.close()


def run(instances_path: str = "instances.py") -> None:
    """Load configured instances and run in parallel with keep-awake."""
    instances = load_instances(instances_path)
    for inst in instances:
        inst.validate()
    logger.info("Executing %d CrowdGen worker instance(s)...", len(instances))
    with keep_awake(), ThreadPoolExecutor(max_workers=max(1, len(instances))) as ex:
        futs = [ex.submit(run_instance, inst) for inst in instances]
        for fut in as_completed(futs):
            fut.result()


if __name__ == "__main__":
    run()
