"""Tests for playback tracking edge cases."""
from unittest.mock import MagicMock, Mock

import xbmc
import pytest
from resources.lib import api
from resources.lib.player import Player


def _make_listitem(program_id, start_offset=None):
    """Build a ListItem mock with the playback properties used by Player."""
    listitem = Mock()
    properties = {'arte_program_id': program_id}
    if start_offset is not None:
        properties['arte_start_offset'] = start_offset
    listitem.getProperty.side_effect = properties.get
    listitem.getPath.return_value = f'https://example.test/{program_id}.m3u8'
    listitem.getVideoInfoTag.return_value.getTitle.return_value = program_id
    listitem.getVideoInfoTag.return_value.getDuration.return_value = 3600
    return listitem


def _make_player(playing_items, playlist=None):
    """Build a Player instance with only the state needed by onAVStarted."""
    player = Player.__new__(Player)
    player.program_data = {}
    player.playlist = playlist
    player.fallback_listitem = None
    player.did_process_first_item_offset = False
    # mocked method name is out of our control, so we disable the pylint warning for it
    setattr(player, 'getPlayingItem', Mock(side_effect=playing_items))
    setattr(player, 'seekTime', Mock())
    player.synch_progress = Mock()
    return player


def test_map_program_data_omits_missing_genre():
    """Trailers without a genre still produce a valid tracking context."""
    # pylint: disable=protected-access
    result = api._map_program_data({
        'program_id': 'PCF2842',
        'stream_url': 'https://example.test/trailer.m3u8',
        'title': "L'homme au cheval blanc",
    })

    assert 'genre' not in result['player']


@pytest.mark.parametrize('playback_data', [
    {
        'event_time': '2026-10-05T12:00:00Z',
        'action': 'VIDEO_PAUSED',
        'timecode': 'invalid',
        'previous_timecode': 10,
    },
    {
        'event_time': '2026-10-05T12:00:00Z',
        'action': 'VIDEO_PAUSED',
        'timecode': 20,
    },
])
def test_track_playback_skips_request_when_payload_data_is_invalid(
        monkeypatch, playback_data):
    """Invalid timecodes or missing payload keys do not escape to Kodi callbacks."""
    post = Mock()
    monkeypatch.setattr(api.requests, 'post', post)

    result = api.track_playback(
        {'token_type': 'Bearer', 'access_token': 'token'},
        {
            'client_id': 'kodi',
            'app_name': 'Arte +7',
            'app_version': '1.0',
            'platform': 'kodi',
            'locale': 'fr',
            'consent': True,
            'user': {'type': 'ANONYMOUS'},
        },
        {
            'program_id': 'program-1',
            'stream_url': 'https://example.test/video.m3u8',
            'title': 'Program',
        },
        playback_data,
    )

    assert result is None
    post.assert_not_called()


def test_terminal_playback_data_uses_last_time_after_kodi_closes_media():
    """Terminal callbacks must not call Kodi getTime after media shutdown."""
    player = Player.__new__(Player)
    player.last_time = 502
    # pylint: disable=protected-access
    player._get_jsonrpc_properties = Mock(return_value={})
    get_time = Mock(side_effect=RuntimeError('Kodi is not playing any media file'))
    setattr(
        player,
        'getTime',
        get_time,
    )

    result = player.build_playback_data('VIDEO_STOPPED')

    assert result['timecode'] == 502
    get_time.assert_not_called()


def test_build_program_data_includes_display_page_context():
    """Tracking data identifies the displayed Kodi page and language."""
    listitem = Mock()
    listitem.getProperty.side_effect = {
        'arte_program_id': 'PCF2842',
    }.get
    listitem.getPath.return_value = 'https://example.test/trailer.m3u8'
    listitem.getVideoInfoTag.return_value.getTitle.return_value = 'Trailer'
    listitem.getVideoInfoTag.return_value.getDuration.return_value = 30

    player = Player.__new__(Player)
    result = player.build_program_data(listitem)

    assert result['page_language'] == 'fr'
    assert result['page_url'] == 'plugin://plugin.video.arteplussept/'
    # pylint: disable=no-member
    xbmc.getInfoLabel.assert_called_with('Container.FolderPath')


def test_first_playlist_item_fallback_seeks_and_next_item_does_not():
    """Recovering a playlist item also recovers its offset, without seeking transitions."""
    recovered_item = _make_listitem('first-program', '1803')
    second_item = _make_listitem('second-program', '420')
    playlist = MagicMock()
    playlist.getposition.side_effect = [0, 1]
    playlist.__getitem__.side_effect = [recovered_item, second_item]
    kodi_item_without_properties = _make_listitem(None)
    player = _make_player(
        [kodi_item_without_properties, second_item],
        playlist=playlist,
    )

    player.onAVStarted()
    player.onAVStarted()

    # methods exist thanks to setattr(player, 'seekTime', Mock())
    # pylint: disable=no-member
    player.seekTime.assert_called_once_with(1803.0)
    assert player.program_data['program_id'] == 'second-program'


def test_first_playlist_item_without_offset_does_not_seek_next_item():
    """An offset on a later playlist item must not trigger a resume seek."""
    first_item = _make_listitem('first-program')
    second_item = _make_listitem('second-program', '420')
    player = _make_player([first_item, second_item])

    player.onAVStarted()
    player.onAVStarted()

    # methods exist thanks to setattr(player, 'seekTime', Mock())
    # pylint: disable=no-member
    player.seekTime.assert_not_called()
