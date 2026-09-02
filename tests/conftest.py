"""Shared Kodi module mocks for tests."""
import sys
import types
from pathlib import Path
from unittest.mock import Mock


fake_xbmc = types.ModuleType("xbmc")
fake_xbmc.LOGERROR = 4
fake_xbmc.LOGWARNING = 3
fake_xbmc.LOGDEBUG = 2
fake_xbmc.log = Mock()
sys.modules["xbmc"] = fake_xbmc

fake_xbmcaddon = types.ModuleType("xbmcaddon")
fake_xbmcaddon.Addon = Mock
sys.modules["xbmcaddon"] = fake_xbmcaddon

fake_xbmcgui = types.ModuleType("xbmcgui")
fake_xbmcgui.ListItem = Mock
sys.modules["xbmcgui"] = fake_xbmcgui

fake_xbmcplugin = types.ModuleType("xbmcplugin")
sys.modules["xbmcplugin"] = fake_xbmcplugin

fake_xbmcvfs = types.ModuleType("xbmcvfs")
fake_xbmcvfs.translatePath = lambda path: path
fake_xbmcvfs.exists = lambda path: Path(path).exists()
fake_xbmcvfs.mkdir = lambda path: Path(path).mkdir()
fake_xbmcvfs.File = open
sys.modules["xbmcvfs"] = fake_xbmcvfs
