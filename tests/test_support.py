"""Shared helpers for Kodi-related tests."""
import io
import json
import sys
import types
from pathlib import Path


def install_fake_kodi_modules():
    """Register lightweight fake Kodi/XBMC modules for importing addon code."""
    fake_xbmc = types.SimpleNamespace(
        LOGERROR=4,
        LOGINFO=1,
        log=lambda message, level=None: None,
    )
    fake_actions = types.SimpleNamespace(
        background=lambda path: f"RunPlugin({path})",
        update_view=lambda url: f"Container.Update({url})",
    )
    fake_plugin = types.SimpleNamespace(
        name="plugin.video.arteplussept",
        url_for=lambda route, **kwargs: f"plugin://plugin.video.arteplussept/{route}",
        get_setting=lambda key, *args, **kwargs: {
            "lang": "fr",
            "quality": "High",
            "show_video_streams": False,
            "user_email": "",
            "loglevel": "DEFAULT",
        }.get(key),
        addon=types.SimpleNamespace(
            getLocalizedString=lambda idx: {
                30012: "Recherche",
                30060: "Lire du début",
                30040: "Ma liste",
                30030: "Reprendre la lecture",
            }.get(idx, str(idx)),
            getAddonInfo=lambda key: "99.99.99",
        ),
    )
    fake_xbmcvfs = types.SimpleNamespace(
        File=lambda path, mode: io.StringIO(),
        exists=lambda path: True,
        mkdir=lambda path: None,
    )
    fake_xbmcgui = types.SimpleNamespace(
        File=lambda path, mode: io.StringIO(),
        exists=lambda path: True,
        mkdir=lambda path: None,
    )

    fake_xbmcswift2 = types.ModuleType("xbmcswift2")
    fake_xbmcswift2.xbmc = fake_xbmc
    fake_xbmcswift2.actions = fake_actions
    fake_xbmcswift2.Plugin = fake_plugin
    fake_xbmcswift2.xbmcvfs = fake_xbmcvfs
    fake_xbmcswift2.xbmcgui = fake_xbmcgui

    fake_xbmcmixin = types.ModuleType("xbmcmixin")
    fake_xbmcmixin.XBMCMixin = object

    fake_listitem = types.ModuleType("listitem")
    fake_listitem.ListItem = object

    fake_logger = types.ModuleType("logger")
    fake_logger.log = object
    fake_logger.setup_log = lambda p: None

    sys.modules["xbmcmixin"] = fake_xbmcmixin
    sys.modules["xbmcswift2.xbmcmixin"] = fake_xbmcmixin
    sys.modules["xbmcswift2"] = fake_xbmcswift2
    sys.modules["listitem"] = fake_listitem
    sys.modules["logger"] = fake_logger


def load_json(name):
    """Load a JSON fixture by name."""
    base = Path(__file__).parent / "fixtures"
    with (base / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)
