"""
Test module for the ArteLiveItem mapper.
"""
from unittest.mock import Mock
# pylint: disable=import-error
import pytest
from tests.test_support import install_fake_kodi_modules, load_json

install_fake_kodi_modules()

# Need to mock environment before importing the module under test
# So, ignore the E408 warning for import order PyLint and Flake8
# pylint: disable=wrong-import-position, wrong-import-order, no-name-in-module
from resources.lib.mapper.arteliveitem import ArteLiveItem  # noqa: E402


@pytest.fixture(name="plugin")
def plugin_fixture():
    """
    Create a mock plugin object with the necessary attributes and methods for testing.
    """
    plugin = Mock()
    plugin.url_for = Mock(return_value="plugin://mocked_route")
    plugin.name = "plugin.video.arteplussept"
    plugin.addon = Mock()
    plugin.addon.getAddonInfo = Mock(return_value="99.99.99")
    plugin.addon.getLocalizedString = Mock(return_value="My mocked localized string")
    return plugin


@pytest.mark.parametrize("payload, expected", [
    ("live_wo_stream_with_program-api.json", "live_wo_stream_with_program-xbmc.json"),
    ("live_with_streams-api.json", "live_with_streams-xbmc.json")
])
def test_build_item_live_contract(plugin, payload, expected):
    """Test the build_item_live method of ArteLiveItem for contract compliance."""
    item = ArteLiveItem(plugin, load_json(payload).get('data'))

    result = item.build_item_live(quality="SQ", audio_slot="1")

    expected_json = load_json(expected)
    # Normalize context_menu array into tuple
    if "context_menu" in expected_json:
        expected_json["context_menu"] = [tuple(cm) for cm in expected_json.get("context_menu", [])]

    # path is coming from plugin fixture, it needs to be tested live or with xbmcswift2 CLI
    assert result == expected_json
