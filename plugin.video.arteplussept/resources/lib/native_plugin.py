"""Lightweight native Plugin replacement for xbmcswift2 routing/navigation.
This provides:
- Plugin.route(path, name=...) decorator to register handlers
- Plugin.run() to dispatch based on sys.argv
- Plugin.url_for(route_name, **kwargs) to build plugin URLs
- Minimal helpers: set_content, add_to_playlist=>map_collection_to_playlist, get_storage

This is intentionally minimal and tailored to this addon
to remove the xbmcswift2 routing dependency.
"""
import json
import os
import sys
import time
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs


class RoutingMixin:
    """Routing and playback helpers for native Kodi plugin URLs."""

    def __init__(self, *args, **kwargs):
        self.base_url = sys.argv[0]
        try:
            self.handle = int(sys.argv[1])
        # pylint: disable=broad-exception-caught
        except Exception:
            self.handle = None
        self._routes = {}
        self._url_paths = {}
        super().__init__(*args, **kwargs)

    def route(self, path, name=None):
        """Decorator to register route handlers."""
        def decorator(func):
            route_name = name or func.__name__
            self._routes[route_name] = func
            self._url_paths[route_name] = path
            return func

        return decorator

    def url_for(self, route_name, **kwargs):
        """Build a plugin URL for a registered route."""
        params = {'route': route_name}
        for key, value in kwargs.items():
            params[key] = value
        return self.base_url + self._url_paths.get(route_name, '') + '?' \
            + urllib.parse.urlencode(params)

    def map_collection_to_playlist(self, collection):
        """Add items to the video playlist."""
        # Empty playlist, otherwise requested video is present twice in the playlist
        pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        for item in collection or []:
            pl.add(item.getPath(), item)
        return pl

    def play_video(self, item):
        """Play a dictionary-based playable item with metadata."""
        if not isinstance(item, dict):
            return False
        path = item.getPath()
        if not path:
            return False
        try:
            xbmc.Player().play(str(path), item)
            return True
        # pylint: disable=broad-exception-caught
        except Exception:
            return False

    def set_content(self, content):
        """Set the content type for the current directory (e.g., 'movies', 'tvshows')."""
        if self.handle is not None and content:
            xbmcplugin.setContent(self.handle, content)

    def run(self):
        """Dispatch to a registered route based on the 'route' query parameter."""
        self.handle = int(sys.argv[1]) if len(sys.argv) > 1 else None
        params = {}
        route = ''
        # route is in sys.argv[2] when opening the plugin
        if len(sys.argv) > 2 and sys.argv[2]:
            raw_route = sys.argv[2][1:]  # Remove leading '?'
            params = urllib.parse.parse_qs(raw_route)
            params = {
                key: value[0] if isinstance(value, list) and len(value) > 0
                else value for key, value in params.items()
            }
            route = params.pop('route', None)
        # route is in sys.argv[0] from settings with runplugin:// (and sys.argv[2] is empty)
        elif sys.argv[0]:
            route = urllib.parse.urlparse(sys.argv[0]).path

        if route == '/' or route is None:
            route = 'index'

        handler = self._routes.get(route)
        if handler is None:
            xbmc.log(f"No handler for route '{route}'", xbmc.LOGERROR)
            return

        try:
            result = handler(**params)
        except TypeError:
            result = handler()

        if self.handle is not None:
            if isinstance(result, list):
                for item in result:
                    path = item.getPath()
                    is_playable = item.getProperty('is_playable') == 'True'
                    xbmcplugin.addDirectoryItem(
                        handle=self.handle, url=path, listitem=item, isFolder=not is_playable)
                xbmcplugin.endOfDirectory(self.handle)
            elif isinstance(result, xbmcgui.ListItem):
                xbmcplugin.setResolvedUrl(self.handle, True, result)


# pylint: disable=too-few-public-methods
class StorageMixin:
    """Addon profile storage and settings helpers."""

    def __init__(self, *args, **kwargs):
        try:
            self.storage_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        # pylint: disable=broad-exception-caught
        except Exception:
            self.storage_path = xbmcvfs.translatePath('special://home/')
        self._storage = {}
        super().__init__(*args, **kwargs)

    def _ensure_storage_dir(self):
        storage_dir = os.path.join(self.storage_path, 'storage')
        try:
            if not xbmcvfs.exists(storage_dir):
                xbmcvfs.mkdir(storage_dir)
        # pylint: disable=broad-exception-caught
        except Exception:
            os.makedirs(storage_dir, exist_ok=True)
        return storage_dir

    def _storage_file_path(self, key):
        return os.path.join(self._ensure_storage_dir(), f"{key}.json")

    def get_storage(self, key, ttl=None):
        """File-backed storage with TTL support (TTL in minutes)."""
        if key in self._storage:
            return self._storage[key]

        file_path = self._storage_file_path(key)

        class FileStorageDict(dict):
            """Dictionary that automatically saves to a JSON file on changes."""
            def __init__(self, path, initial):
                super().__init__(initial or {})
                self._path = path

            def _save(self):
                payload = {'created': int(time.time()), 'value': dict(self)}
                with xbmcvfs.File(self._path, 'w') as handle:
                    handle.write(json.dumps(payload))

            def __setitem__(self, key_name, value):
                super().__setitem__(key_name, value)
                self._save()

            def __delitem__(self, key_name):
                super().__delitem__(key_name)
                self._save()

            def clear(self):
                super().clear()
                self._save()

            def update(self, *args, **kwargs):
                super().update(*args, **kwargs)
                self._save()

            def pop(self, *args, **kwargs):
                value = super().pop(*args, **kwargs)
                self._save()
                return value

        storage = FileStorageDict(file_path, {})
        if xbmcvfs.exists(file_path):
            with xbmcvfs.File(file_path, 'r') as handle:
                content = handle.read()
            if content:
                data = json.loads(content)
                created = int(data.get('created', 0))
                value = data.get('value', {})
                if ttl is not None and int(time.time()) - created > int(ttl) * 60:
                    value = {}
                storage = FileStorageDict(file_path, value)

        # try:
        #     storage._save()
        # except Exception:
        #     pass
        self._storage[key] = storage
        return storage


class Plugin(RoutingMixin, StorageMixin):
    """
    Composite native plugin implementation preserving xbmcswift2-compatible API.
    Notification helpers for addon UI messages.
    """

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        super().__init__()

    def notify(self, msg, image=None, mtime=5000):
        """Show a notification message in Kodi."""
        xbmcgui.Dialog().notification(self.addon.getAddonInfo('name'), msg, image, mtime)


# convenience single instance for modules that expect Plugin in the module scope
_default_plugin = Plugin()
