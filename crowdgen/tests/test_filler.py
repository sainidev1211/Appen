"""Tests for Maven caption and form filler utility."""

from unittest.mock import MagicMock, patch

from crowdgen_automation.tasks.filler import fill_maven_form


def test_fill_maven_form_fills_all_fields() -> None:
    """Verify fill_maven_form selects No Issue and types detailed then short captions."""
    mock_ctx = MagicMock()
    mock_no_issue = MagicMock()
    mock_detailed = MagicMock()
    mock_short = MagicMock()
    mock_angle = MagicMock()

    def locator_mock(sel: str) -> MagicMock:
        loc = MagicMock()
        if "No Issue" in sel:
            loc.first = mock_no_issue
        elif "detailed" in sel:
            loc.first = mock_detailed
        elif "short" in sel:
            loc.first = mock_short
        else:
            loc.first = mock_angle
        return loc

    mock_ctx.locator.side_effect = locator_mock
    mock_no_issue.is_visible.return_value = True
    mock_detailed.is_visible.return_value = True
    mock_short.is_visible.return_value = True
    mock_angle.is_visible.return_value = True

    with patch("time.sleep"):
        fill_maven_form(
            mock_ctx,
            {
                "detailed_caption": "Detailed description with over twenty five words.",
                "short_caption": "A concise short sentence.",
                "camera_angle": "low-angle view",
            },
        )

    mock_no_issue.click.assert_called_once()
    mock_detailed.press_sequentially.assert_called_with(
        "Detailed description with over twenty five words.", delay=25, timeout=45000
    )
    mock_short.press_sequentially.assert_called_with(
        "A concise short sentence.", delay=25, timeout=45000
    )
    mock_angle.press_sequentially.assert_called_with(
        "low-angle view", delay=25, timeout=45000
    )


def test_fill_maven_form_unusable_quality_flags_issue() -> None:
    """Verify unusable quality flags Image Check and leaves captions blank."""
    mock_ctx = MagicMock()
    mock_issue = MagicMock()
    mock_detailed = MagicMock()
    mock_short = MagicMock()

    def locator_mock(sel: str) -> MagicMock:
        loc = MagicMock()
        if "Yes" in sel or "Issue" in sel:
            loc.first = mock_issue
        elif "detailed" in sel:
            loc.first = mock_detailed
        elif "short" in sel:
            loc.first = mock_short
        return loc

    mock_ctx.locator.side_effect = locator_mock
    mock_issue.is_visible.return_value = True

    fill_maven_form(mock_ctx, {"unusable_quality": "true"})

    mock_issue.click.assert_called_once()
    mock_detailed.press_sequentially.assert_not_called()
    mock_short.press_sequentially.assert_not_called()


def test_fill_maven_form_dense_document_tags_dense() -> None:
    """Verify dense document tags Dense radio button and leaves captions blank."""
    mock_ctx = MagicMock()
    mock_dense = MagicMock()
    mock_detailed = MagicMock()
    mock_short = MagicMock()

    def locator_mock(sel: str) -> MagicMock:
        loc = MagicMock()
        if "Dense" in sel:
            loc.first = mock_dense
        elif "detailed" in sel:
            loc.first = mock_detailed
        elif "short" in sel:
            loc.first = mock_short
        return loc

    mock_ctx.locator.side_effect = locator_mock
    mock_dense.is_visible.return_value = True

    fill_maven_form(mock_ctx, {"is_dense": "true"})

    mock_dense.click.assert_called_once()
    mock_detailed.press_sequentially.assert_not_called()
    mock_short.press_sequentially.assert_not_called()
