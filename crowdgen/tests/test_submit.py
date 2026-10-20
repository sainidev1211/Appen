"""Tests for submission and timer countdown."""

from unittest.mock import MagicMock, patch

from crowdgen_automation.tasks.submit import (
    get_page_remaining_seconds,
    submit_task,
    wait_for_target_timer,
)


def test_get_page_remaining_seconds() -> None:
    """Verify reads remaining seconds from page DOM evaluation."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = 128
    assert get_page_remaining_seconds(mock_page) == 128

    mock_page.evaluate.side_effect = RuntimeError("DOM error")
    assert get_page_remaining_seconds(mock_page) is None


def test_wait_for_target_timer_reaches_target() -> None:
    """Verify wait_for_target_timer stops when remaining <= target."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = 130
    with patch("time.sleep") as mock_sleep:
        wait_for_target_timer(mock_page, start_time=0.0, target_remaining_sec=130)
        mock_sleep.assert_not_called()


def test_submit_task_review_mode() -> None:
    """Verify semi-autonomous mode does not click submit."""
    mock_ctx = MagicMock()
    res = submit_task(mock_ctx, start_time=0.0, auto_submit=False)
    assert res is True
    mock_ctx.locator.assert_not_called()


def test_submit_task_auto_submit_success() -> None:
    """Verify clicks submit and confirms modal when auto_submit is True."""
    mock_ctx = MagicMock()
    mock_sub = MagicMock()
    mock_conf = MagicMock()

    mock_sub.is_visible.return_value = True
    mock_conf.is_visible.return_value = True

    def locator_side_effect(sel: str) -> MagicMock:
        loc = MagicMock()
        if "Submit" in sel:
            loc.first = mock_sub
        else:
            loc.first = mock_conf
        return loc

    mock_ctx.locator.side_effect = locator_side_effect
    with patch("crowdgen_automation.tasks.submit.wait_for_target_timer") as mock_wait:
        res = submit_task(mock_ctx, start_time=0.0, auto_submit=True, target_remaining_sec=0)
        assert res is True
        mock_wait.assert_not_called()
        mock_sub.click.assert_called_once()
        mock_conf.click.assert_called_once()
