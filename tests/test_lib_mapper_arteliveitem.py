"""
Test module for the ArteLiveItem mapper.
"""
# Standard imports
import sys
import types
from pathlib import Path
from unittest.mock import Mock
# Third-party imports
import json
# pylint: disable=import-error
import pytest

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

# Need to mock environment before importing the module under test
# So, ignore the E408 warning for import order PyLint and Flake8
# pylint: disable=wrong-import-position
from resources.lib.mapper.arteliveitem import ArteLiveItem  # noqa: E402


def load_json(name):
    """Load a JSON fixture by name (without extension)."""
    base = Path(__file__).parent / "fixtures"
    with (base / f"{name}").open("r", encoding="utf-8") as f:
        return json.load(f)


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
