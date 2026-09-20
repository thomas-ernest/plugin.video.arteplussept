"""Tests for playback tracking edge cases."""
from unittest.mock import Mock

import xbmc
from resources.lib import api
from resources.lib.player import Player


def test_map_program_data_omits_missing_genre():
    """Trailers without a genre still produce a valid tracking context."""
    result = api._map_program_data({
        'program_id': 'PCF2842',
        'stream_url': 'https://example.test/trailer.m3u8',
        'title': "L'homme au cheval blanc",
    })

    assert 'genre' not in result['player']


def test_terminal_playback_data_uses_last_time_after_kodi_closes_media():
    """Terminal callbacks must not call Kodi getTime after media shutdown."""
    player = Player.__new__(Player)
    player.last_time = 502
    player._get_jsonrpc_properties = Mock(return_value={})
    player.getTime = Mock(side_effect=RuntimeError('Kodi is not playing any media file'))

    result = player.build_playback_data('VIDEO_STOPPED')

    assert result['timecode'] == 502
    player.getTime.assert_not_called()


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
    xbmc.getInfoLabel.assert_called_with('Container.FolderPath')
