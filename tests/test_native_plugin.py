"""Tests for the native plugin storage helpers."""
import tempfile
from unittest.mock import Mock

from resources.lib.native_plugin import StorageMixin  # noqa: E402


def test_cached_storage_rechecks_requested_ttl(monkeypatch):
    """A cached value loaded without TTL expires when later requested with TTL."""
    with tempfile.TemporaryDirectory() as storage_path:
        plugin = StorageMixin.__new__(StorageMixin)
        plugin.addon = Mock()
        plugin.addon.getAddonInfo.return_value = storage_path
        monkeypatch.setattr("resources.lib.native_plugin.time.time", lambda: 1000)
        StorageMixin.__init__(plugin)
        storage = plugin.get_storage("token")
        storage["user@example.com"] = {"access_token": "token"}

        monkeypatch.setattr("resources.lib.native_plugin.time.time", lambda: 1061)
        expired_storage = plugin.get_storage("token", ttl=1)

        assert expired_storage == {}
        assert expired_storage is not storage
