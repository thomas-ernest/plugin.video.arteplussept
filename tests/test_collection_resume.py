"""Tests for resume position selection in collection playlists."""
from unittest.mock import Mock

# pylint: disable=import-error, no-name-in-module
from resources.lib.mapper.mapper import get_collection_resume_position


def listitem(start_offset=None, duration=1000):
    """Build an item exposing its Arte resume offset and total duration."""
    item = Mock()
    item.getProperty.return_value = '' if start_offset is None else str(start_offset)
    item.getVideoInfoTag.return_value.getDuration.return_value = duration
    return item


def test_explicit_program_position_overrides_cached_progress():
    """An explicit episode selection has the highest priority."""
    result = get_collection_resume_position(
        [listitem(450), listitem(0)], {'selected': 1}, 'selected'
    )

    assert result == 1


def test_first_uncompleted_program_is_resumed():
    """The first item below the completion threshold is selected."""
    result = get_collection_resume_position(
        [listitem(1000), listitem(450), listitem(0)], {},
    )

    assert result == 1


def test_progress_over_95_percent_is_skipped():
    """A completed item is skipped in favor of the next unwatched item."""
    result = get_collection_resume_position(
        [listitem(960), listitem(0)], {},
    )

    assert result == 1


def test_unknown_progress_is_treated_as_unwatched():
    """Items with no progress signal are eligible as unwatched items."""
    result = get_collection_resume_position(
        [listitem(), listitem()], {}
    )

    assert result == 0


def test_exactly_95_percent_is_considered_completed():
    """An item at the completion threshold is skipped."""
    result = get_collection_resume_position(
        [listitem(950), listitem(0)], {},
    )

    assert result == 1


def test_missing_program_id_is_logged_in_helper_before_auto_resume(monkeypatch):
    """An invalid explicit id is logged where fallback selection occurs."""
    log = Mock()
    monkeypatch.setattr('resources.lib.mapper.mapper.xbmc.log', log)

    result = get_collection_resume_position(
        [listitem(450)], {}, 'missing', collection_id='collection-1'
    )

    assert result == 0
    assert 'Unable to find program missing in collection collection-1.' \
        in log.call_args_list[0].args[0]
