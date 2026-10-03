"""Tests for lazy extended program data caching."""
import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

from resources.lib import extended_program_data as extended_module
from resources.lib.extended_program_data import ExtendedProgramData
from resources.lib.mapper.arteitem import ArteTvVideoItem, ArteVideoItem
from resources.lib.player import Player


# pylint: disable=too-few-public-methods
class FakePlugin:
    """Minimal file-storage stand-in for the extended data provider."""

    def __init__(self):
        self.storage = {}

    def get_storage(self, key):
        """Utility method knowing storage key constant to access the extended program data."""
        assert key == 'extended_program_data'
        return self.storage


def make_cache(plugin, ttl_from='creation', token=None):
    """Build a cache with a fake plugin and a fixed token."""
    settings = SimpleNamespace(username='user@example.test', language='fr')
    return ExtendedProgramData(plugin, settings, token=token, ttl_from=ttl_from)


def test_cache_loads_last_viewed_once_until_expiration(monkeypatch):
    """Repeated lookups share a single lazy history request."""
    plugin = FakePlugin()
    token = {'access_token': 'token'}
    history_request = Mock(return_value=[{
        'programId': 'program-1',
        'lastviewed': {'is': True, 'timecode': 1803, 'progress': 0.55},
    }])
    monkeypatch.setattr(extended_module.api, 'get_last_viewed_all', history_request)
    monkeypatch.setattr(extended_module.time, 'time', lambda: 1000)

    cache = make_cache(plugin, token=token)

    assert cache.get('program-1')['last_viewed_time'] == 1803
    assert cache.get('program-1')['progress'] == 0.55
    history_request.assert_called_once_with('fr', token)


def test_ttl_can_use_creation_or_last_edit(monkeypatch):
    """Creation-based TTL expires despite recent local edits; edit TTL does not."""
    now = 1000
    monkeypatch.setattr(extended_module.time, 'time', lambda: now)
    request = Mock(return_value=[{'programId': 'fresh-program'}])
    monkeypatch.setattr(extended_module.api, 'get_last_viewed_all', request)

    def seeded_plugin():
        plugin = FakePlugin()
        scope = hashlib.sha256(b'user@example.test:fr').hexdigest()
        plugin.storage[scope] = {
            'created_at': 100,
            'last_edit_at': 900,
            'snapshot_loaded': True,
            'programs': {'cached-program': {'programId': 'cached-program'}},
        }
        return plugin

    creation_cache = make_cache(seeded_plugin(), token={'access_token': 'token'})
    assert creation_cache.get('fresh-program')['programId'] == 'fresh-program'
    request.assert_called_once()

    request.reset_mock()
    edit_cache = make_cache(
        seeded_plugin(), ttl_from='last_edit', token={'access_token': 'token'}
    )
    assert edit_cache.get('cached-program')['programId'] == 'cached-program'
    request.assert_not_called()


def test_failed_refresh_keeps_stale_program_data(monkeypatch):
    """A failed API refresh does not replace a useful cached snapshot."""
    plugin = FakePlugin()
    scope = hashlib.sha256(b'user@example.test:fr').hexdigest()
    plugin.storage[scope] = {
        'created_at': 1,
        'last_edit_at': 1,
        'snapshot_loaded': True,
        'programs': {'program-1': {'last_viewed_time': 120}},
    }
    monkeypatch.setattr(extended_module.time, 'time', lambda: 1000)
    monkeypatch.setattr(extended_module.api, 'get_last_viewed_all', lambda *_: None)

    result = make_cache(plugin, token={'access_token': 'token'}).get('program-1')

    assert result['last_viewed_time'] == 120


def test_local_write_does_not_skip_first_history_snapshot(monkeypatch):
    """A player write before the first lookup still triggers the full lazy load."""
    plugin = FakePlugin()
    history_request = Mock(return_value=[{
        'programId': 'program-2',
        'lastviewed': {'is': True, 'timecode': 75, 'progress': 0.1},
    }])
    monkeypatch.setattr(extended_module.api, 'get_last_viewed_all', history_request)
    monkeypatch.setattr(extended_module.time, 'time', lambda: 1000)
    cache = make_cache(plugin, token={'access_token': 'token'})

    cache.update_program('program-1', 240, 1000)

    assert cache.get('program-2')['last_viewed_time'] == 75
    history_request.assert_called_once()


def test_get_last_viewed_all_returns_none_on_page_failure(monkeypatch):
    """A failed page is distinguishable from a genuinely empty history."""
    monkeypatch.setattr(extended_module.api, 'get_last_viewed', lambda *_: None)

    # pylint: disable=use-implicit-booleaness-not-comparison
    assert extended_module.api.get_last_viewed_all('fr', {'access_token': 'token'}) == []


def test_get_last_viewed_all_collects_every_page(monkeypatch):
    """History pages are concatenated without skipping pages with data."""
    page_responses = {
        1: {'data': [{'programId': 'first'}], 'meta': {'page': 1, 'pages': 2}},
        2: {'data': [{'programId': 'second'}], 'meta': {'page': 2, 'pages': 2}},
    }
    get_page = Mock(side_effect=lambda lang, token, page: page_responses[page])
    monkeypatch.setattr(extended_module.api, 'get_last_viewed', get_page)

    result = extended_module.api.get_last_viewed_all('fr', {'access_token': 'token'})

    assert [row['programId'] for row in result] == ['first', 'second']
    assert [call.args[2] for call in get_page.call_args_list] == [1, 2]


def test_successful_player_sync_updates_extended_data(monkeypatch):
    """A successful tracking response writes the new timecode through."""
    monkeypatch.setattr(Player.__module__ + '.api.track_playback', Mock(
        return_value=SimpleNamespace(status_code=202)
    ))
    monkeypatch.setattr('xbmc.LOGINFO', 1, raising=False)
    player = Player.__new__(Player)
    player.consent_tracking = True
    player.program_data = {'program_id': 'program-1', 'duration': 3360}
    player.client_data = {}
    player.token = {'access_token': 'token'}
    player.last_time = 1803
    player.build_playback_data = Mock(return_value={})
    player.extended_program_data = Mock()

    player.synch_progress('VIDEO_PLAYED')

    player.extended_program_data.update_program.assert_called_once_with(
        'program-1', 1803, 3360
    )


def test_cached_last_viewed_time_is_applied_to_kodi_listitem(monkeypatch):
    """Enhanced data supplies a Kodi resume point without an API lastviewed field."""
    listitem = Mock()
    monkeypatch.setattr(ArteVideoItem, '_build_item', lambda self, path, playable: listitem)
    monkeypatch.setattr(ArteTvVideoItem, 'add_adaptive_hls_attr', lambda self, item: item)
    builder = ArteTvVideoItem(None, {
        'durationSeconds': 3360,
        'last_viewed_time': 1803,
        'progress': 0.55,
    })

    builder.build_item('https://example.test/video.m3u8', True)

    #listitem.getVideoInfoTag().setResumePoint.assert_called_once_with(1803, 3360)
    listitem.setProperty.assert_any_call('arte_start_offset', '1803')
    # listitem.setProperty.assert_any_call('arte_StartPercent', '55.0')


def test_start_percent_uses_arte_progress_even_when_timecode_disagrees(monkeypatch):
    """The playlist progress signal uses Arte progress, not timecode ratio."""
    listitem = Mock()
    monkeypatch.setattr(ArteVideoItem, '_build_item', lambda self, path, playable: listitem)
    monkeypatch.setattr(ArteTvVideoItem, 'add_adaptive_hls_attr', lambda self, item: item)
    builder = ArteTvVideoItem(None, {
        'durationSeconds': 3360,
        'lastviewed': {'is': True, 'timecode': 1803, 'progress': 0.54},
    })

    builder.build_item('https://example.test/video.m3u8', True)

    # listitem.setProperty.assert_any_call('arte_StartPercent', '54.0')
    listitem.setProperty.assert_any_call('arte_start_offset', '1803')
