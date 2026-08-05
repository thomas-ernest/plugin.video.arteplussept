"""Contract test for the home page builder."""
import json
import sys
import types
import urllib.parse
from pathlib import Path
from unittest.mock import Mock

import pytest

# Fake xbmcswift2 imports used by resources.lib.view and mapper modules.
fake_xbmc = types.SimpleNamespace(
    LOGERROR=4,
    LOGINFO=1,
    log=lambda message, level=None: None,
)
fake_actions = types.SimpleNamespace(
    background=lambda path: f"RunPlugin({path})",
    update_view=lambda url: f"Container.Update({url})"
)
fake_plugin = types.SimpleNamespace(
    name='plugin.video.arteplussept',
    url_for=lambda route, **kwargs: f"plugin://plugin.video.arteplussept/{route}",
    get_setting=lambda key, *args, **kwargs: {
        'lang': 'fr',
        'quality': 'High',
        'show_video_streams': False,
        'user_email': '',
        'loglevel': 'DEFAULT'
    }.get(key),
    addon=types.SimpleNamespace(
        getLocalizedString=lambda idx: {
            30012: 'Recherche',
            30060: 'Lire du début',
            30040: 'Purger mes favoris Arte',
            30030: 'Purger mon historique'
        }.get(idx, str(idx)),
        getAddonInfo=lambda key: '99.99.99'
    )
)
fake_xbmcvfs = types.SimpleNamespace(
    # pylint: disable=unnecessary-lambda, unspecified-encoding
    File=lambda path, mode: open(path, mode),
    exists=lambda path: True,
    mkdir=lambda path: None,
)
fake_xbmcgui = types.SimpleNamespace(
    # pylint: disable=unnecessary-lambda, unspecified-encoding
    File=lambda path, mode: open(path, mode),
    exists=lambda path: True,
    mkdir=lambda path: None,
)

fake_xbmcswift2 = types.ModuleType("xbmcswift2")
fake_xbmcswift2.xbmc = fake_xbmc
fake_xbmcswift2.actions = fake_actions
fake_xbmcswift2.Plugin = fake_plugin
fake_xbmcswift2.xbmcvfs = fake_xbmcvfs
fake_xbmcswift2.xbmcgui = fake_xbmcgui
sys.modules["xbmcswift2"] = fake_xbmcswift2

# Register fake modules: xbmcmixin, listitem, and logger to avoid import errors during testing
fake_xbmcmixin = types.ModuleType("xbmcmixin")
fake_xbmcmixin.XBMCMixin = object
sys.modules["xbmcmixin"] = fake_xbmcmixin
sys.modules["xbmcswift2.xbmcmixin"] = fake_xbmcmixin

fake_listitem = types.ModuleType("listitem")
fake_listitem.ListItem = object
sys.modules["listitem"] = fake_listitem

fake_logger = types.ModuleType("logger")
fake_logger.log = object
fake_logger.setup_log = lambda p: None
sys.modules["logger"] = fake_logger

# Need to create mocks before importing
# pylint: disable=no-name-in-module, import-error, wrong-import-position
from resources.lib import api  # noqa: E402
# pylint: disable=no-name-in-module, import-error, wrong-import-position
from resources.lib import view  # noqa: E402
# pylint: disable=no-name-in-module, import-error, wrong-import-position
from resources.lib.settings import Settings  # noqa: E402


def load_json(name):
    """Load a JSON fixture by name."""
    base = Path(__file__).parent / "fixtures"
    with (base / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def plugin_url_for(route, **kwargs):
    """Simulate plugin URL generation for routes used by build_home_page."""
    if route == 'init_search':
        return 'plugin://plugin.video.arteplussept/search'
    if route == 'play_live':
        stream_url = urllib.parse.quote(str(kwargs['stream_url']), safe='')
        mpaa = urllib.parse.quote(str(kwargs['mpaa']), safe='')
        return f'plugin://plugin.video.arteplussept/play_live/{stream_url}/{mpaa}'
    if route == 'play_from':
        kind = urllib.parse.quote(str(kwargs['kind']), safe='')
        program_id = urllib.parse.quote(str(kwargs['program_id']), safe='')
        mpaa = urllib.parse.quote(str(kwargs['mpaa']), safe='')
        play_from = urllib.parse.quote(str(kwargs['play_from']), safe='')
        return f'plugin://plugin.video.arteplussept/play/{kind}/{program_id}/{mpaa}/{play_from}'
    if route == 'cached_category':
        zone_id = urllib.parse.quote(str(kwargs['zone_id']), safe='')
        return f'plugin://plugin.video.arteplussept/category/cached/{zone_id}'
    if route == 'api_category':
        category_code = urllib.parse.quote(str(kwargs['category_code']), safe='')
        return f'plugin://plugin.video.arteplussept/category/api/{category_code}'
    if route == 'favorites_default':
        return 'plugin://plugin.video.arteplussept/favorites'
    if route == 'last_viewed_default':
        return 'plugin://plugin.video.arteplussept/last_viewed'
    if route == 'favorites':
        page = urllib.parse.quote(str(kwargs.get('page', '1')), safe='')
        return f'plugin://plugin.video.arteplussept/favorites/{page}'
    if route == 'last_viewed':
        page = urllib.parse.quote(str(kwargs.get('page', '1')), safe='')
        return f'plugin://plugin.video.arteplussept/last_viewed/{page}'
    if route == 'category_page':
        zone_id = urllib.parse.quote(str(kwargs['zone_id']), safe='')
        page = urllib.parse.quote(str(kwargs['page']), safe='')
        page_id = urllib.parse.quote(str(kwargs['page_id']), safe='')
        return f'plugin://plugin.video.arteplussept/category/page/{zone_id}/{page}/{page_id}'
    return f"plugin://plugin.video.arteplussept/{route}"


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
