"""Lightweight native Plugin replacement for xbmcswift2 routing/navigation.
This provides:
- Plugin.route(path, name=...) decorator to register handlers
- Plugin.run() to dispatch based on sys.argv
- Plugin.url_for(route_name, **kwargs) to build plugin URLs
- Minimal helpers: set_content, set_resolved_url, play_video, add_to_playlist, get_storage, finish

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
        except Exception:
            self.handle = None
        self._routes = {}
        super().__init__(*args, **kwargs)

    def route(self, path, name=None):
        """Decorator to register route handlers."""
        def decorator(func):
            route_name = name or func.__name__
            self._routes[route_name] = func
            return func

        return decorator

    def url_for(self, route_name, **kwargs):
        params = {'route': route_name}
        for key, value in kwargs.items():
            params[key] = value
        return self.base_url + '?' + urllib.parse.urlencode(params)

    def add_to_playlist(self, collection):
        """Add items (list of dict items with 'path') to the video playlist."""
        pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        results = []
        for item in collection or []:
            path = item.get('path')
            li = xbmcgui.ListItem(label=item.get('label', ''))
            thumb = item.get('thumbnail') or (item.get('properties') or {}).get('fanart_image')
            if thumb:
                li.setArt({'thumb': thumb})
            info = item.get('info')
            if info:
                try:
                    li.setInfo('video', info)
                except Exception:
                    pass
            try:
                pl.add(path, li)
                results.append(li)
            except Exception:
                xbmc.log(f"Could not add to playlist: {path}", xbmc.LOGWARNING)
        return results

    def set_resolved_url(self, listitem=None):
        if self.handle is None:
            return False
        if listitem is None:
            xbmcplugin.setResolvedUrl(self.handle, True, xbmcgui.ListItem())
        else:
            if isinstance(listitem, dict):
                li = xbmcgui.ListItem(label=listitem.get('label', ''))
                xbmcplugin.setResolvedUrl(self.handle, True, li)
            else:
                xbmcplugin.setResolvedUrl(self.handle, True, listitem)
        return True

    def play_video(self, listitem):
        return self.set_resolved_url(listitem)

    def finish(self, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            return args[0]
        return None

    def set_content(self, content):
        if self.handle is not None and content:
            try:
                xbmcplugin.setContent(self.handle, content)
            except Exception:
                pass

    def run(self):
        """Dispatch to a registered route based on the 'route' query parameter."""
        params = {}
        if len(sys.argv) > 2 and sys.argv[2]:
            params = urllib.parse.parse_qs(sys.argv[2][1:])
            params = {key: value[0] if isinstance(value, list) and len(value) > 0 else value
                      for key, value in params.items()}
        route = params.pop('route', None)
        if route is None:
            route = 'index'
        handler = self._routes.get(route)
        if handler is None:
            xbmc.log(f"No handler for route '{route}'", xbmc.LOGERROR)
            return
        try:
            result = handler(**params)
        except TypeError:
            result = handler()
        if isinstance(result, list) and self.handle is not None:
            for item in result:
                try:
                    label = item.get('label')
                    path = item.get('path')
                    is_playable = item.get('is_playable', False)
                    li = xbmcgui.ListItem(label)
                    thumb = item.get('thumbnail') or \
                        (item.get('properties') or {}).get('fanart_image')
                    if thumb:
                        li.setArt({'thumb': thumb})
                    info = item.get('info')
                    if info:
                        try:
                            li.setInfo('video', info)
                        except Exception:
                            pass
                    ctx = item.get('context_menu')
                    if ctx:
                        try:
                            li.addContextMenuItems(ctx, replaceItems=False)
                        except Exception:
                            pass
                    xbmcplugin.addDirectoryItem(
                        handle=self.handle, url=path, listitem=li, isFolder=(not is_playable))
                except Exception as exc:
                    xbmc.log(f"Error rendering menu item: {exc}", xbmc.LOGWARNING)
            try:
                xbmcplugin.endOfDirectory(self.handle)
            except Exception:
                pass
        elif isinstance(result, dict) and result.get('path') and result.get('is_playable'):
            li = xbmcgui.ListItem(label=result.get('label', ''))
            xbmcplugin.setResolvedUrl(self.handle, True, li)


class NotificationMixin:
    """Notification helpers for addon UI messages."""

    def __init__(self, *args, **kwargs):
        self.addon = xbmcaddon.Addon()
        super().__init__(*args, **kwargs)

    def notify(self, msg, image=None, mtime=5000):
        try:
            xbmcgui.Dialog().notification(self.addon.getAddonInfo('name'), msg, image, mtime)
        except Exception:
            xbmc.log(f"Notification: {msg}")


class StorageMixin:
    """Addon profile storage and settings helpers."""

    def __init__(self, *args, **kwargs):
        try:
            self.storage_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        except Exception:
            self.storage_path = xbmcvfs.translatePath('special://home/')
        self._storage = {}
        super().__init__(*args, **kwargs)

    def _ensure_storage_dir(self):
        storage_dir = os.path.join(self.storage_path, 'storage')
        try:
            if not xbmcvfs.exists(storage_dir):
                xbmcvfs.mkdir(storage_dir)
        except Exception:
            try:
                os.makedirs(storage_dir, exist_ok=True)
            except Exception:
                pass
        return storage_dir

    def _storage_file_path(self, key):
        return os.path.join(self._ensure_storage_dir(), f"{key}.json")

    def set_setting(self, key, value):
        """Set an addon setting via xbmcaddon API."""
        try:
            self.addon.setSetting(key, str(value) if value is not None else '')
            return True
        except Exception:
            xbmc.log(f"Failed to set setting {key}", xbmc.LOGWARNING)
            return False

    def get_setting(self, key):
        """Get an addon setting via xbmcaddon API."""
        try:
            return self.addon.getSetting(key)
        except Exception:
            xbmc.log(f"Failed to get setting {key}", xbmc.LOGWARNING)
            return None

    def get_storage(self, key, ttl=None):
        """File-backed storage with TTL support (TTL in minutes)."""
        if key in self._storage:
            return self._storage[key]

        file_path = self._storage_file_path(key)

        class FileStorageDict(dict):
            def __init__(self, path, initial):
                super().__init__(initial or {})
                self._path = path

            def _save(self):
                try:
                    payload = {'created': int(time.time()), 'value': dict(self)}
                    with xbmcvfs.File(self._path, 'w') as handle:
                        handle.write(json.dumps(payload))
                except Exception as exc:
                    xbmc.log(f"Failed saving storage file {self._path}: {exc}", xbmc.LOGWARNING)

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
        try:
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
        except Exception as exc:
            xbmc.log(f"Failed loading storage file {file_path}: {exc}", xbmc.LOGWARNING)

        try:
            storage._save()
        except Exception:
            pass
        self._storage[key] = storage
        return storage


class Plugin(RoutingMixin, NotificationMixin, StorageMixin):
    """Composite native plugin implementation preserving xbmcswift2-compatible API."""

    def __init__(self):
        super().__init__()


# convenience single instance for modules that expect Plugin in the module scope
_default_plugin = Plugin()


def get_default_plugin():
    """Singleton plugin"""
    return _default_plugin
