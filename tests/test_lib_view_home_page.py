"""
Contract test for the home page builder.
"""
import urllib.parse
from unittest.mock import Mock
# pylint: disable=import-error
import pytest

from tests.test_support import install_fake_kodi_modules, load_json

install_fake_kodi_modules()

# Mocks are created before importing these files to avoid failures
# pylint: disable=no-name-in-module, import-error, wrong-import-position, wrong-import-order
from resources.lib import api  # noqa: E402
# pylint: disable=no-name-in-module, import-error, wrong-import-position, wrong-import-order
from resources.lib import view  # noqa: E402
# pylint: disable=no-name-in-module, import-error, wrong-import-position, wrong-import-order
from resources.lib.settings import Settings  # noqa: E402


def plugin_url_for(route, **kwargs):
    """Simulate plugin URL generation for routes used by build_home_page."""
    base_url_by_route = {
        'init_search': 'plugin://plugin.video.arteplussept/search',
        'favorites_default': 'plugin://plugin.video.arteplussept/favorites',
        'last_viewed_default': 'plugin://plugin.video.arteplussept/last_viewed',
        'play_live': 'plugin://plugin.video.arteplussept/play_live',
        'play_from': 'plugin://plugin.video.arteplussept/play',
        'cached_category': 'plugin://plugin.video.arteplussept/category/cached',
        'api_category': 'plugin://plugin.video.arteplussept/category/api',
        'favorites': 'plugin://plugin.video.arteplussept/favorites',
        'last_viewed': 'plugin://plugin.video.arteplussept/last_viewed',
        'category_page': 'plugin://plugin.video.arteplussept/category/page',
    }
    url_params_by_route = {
        'play_live': ('stream_url', 'mpaa'),
        'play_from': ('kind', 'program_id', 'mpaa', 'play_from'),
        'cached_category': ('zone_id',),
        'api_category': ('category_code',),
        'favorites': ('page',),
        'last_viewed': ('page',),
        'category_page': ('zone_id', 'page', 'page_id'),
    }

    url = ""
    if route in base_url_by_route:
        base_url = base_url_by_route[route]
        if route in url_params_by_route:
            params = [urllib.parse.quote(str(kwargs[param]), safe='')
                      for param in url_params_by_route[route]]
            url = '/'.join([base_url, *params])
        else:
            url = base_url
    else:
        url = f"plugin://plugin.video.arteplussept/{route}"
    return url


@pytest.fixture(name='plugin')
def plugin_fixture():
    """Create a minimal mock plugin for view and mapper route generation."""
    plugin = Mock()
    plugin.name = 'plugin.video.arteplussept'
    plugin.url_for = Mock(side_effect=plugin_url_for)
    plugin.get_setting = Mock(side_effect=lambda key, *args, **kwargs: {
        'lang': 'fr',
        'quality': 'High',
        'show_video_streams': False,
        'user_email': '',
        'loglevel': 'DEFAULT'
    }.get(key))
    addon = Mock()
    addon.getLocalizedString = Mock(side_effect=lambda idx: {
        30012: 'Recherche',
        30060: 'Lire du début',
        30040: 'Purger mes favoris Arte',
        30030: 'Purger mon historique'
    }.get(idx, str(idx)))
    addon.getAddonInfo = Mock(return_value='99.99.99')
    plugin.addon = addon
    return plugin


def test_build_home_page_contract(plugin, monkeypatch):
    """Ensure build_home_page produces the expected home menu contract."""
    player_data = load_json('artetv_player-api.json').get('data')
    home_data = load_json('artetv_home-api.json')

    monkeypatch.setattr(api, 'player_video', lambda language, program_id: player_data)
    monkeypatch.setattr(api, 'page_content', lambda language: home_data)

    settings = Settings(plugin)
    actual = view.build_home_page(plugin, settings, {})

    expected_json = load_json('index-xbmc.json')
    # Normalize context_menu array into tuple
    for json_item in expected_json:
        if "context_menu" in json_item:
            json_item["context_menu"] = [tuple(cm) for cm in json_item.get("context_menu", [])]

    assert actual == expected_json
