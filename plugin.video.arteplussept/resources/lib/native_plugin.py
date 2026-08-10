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
        xbmc.log(f"Building URL for route '{route_name}' with params: {kwargs}", xbmc.LOGWARNING)
        xbmc.log(f"Registered routes: {self._routes.keys()}", xbmc.LOGWARNING)
        params = {'route': route_name}
        for key, value in kwargs.items():
            params[key] = value
        # return (self.base_url + 
        #         '/' + self._url_paths.get(route_name, '') +
        #         '?' + urllib.parse.urlencode(params))
        return self.base_url + self._url_paths.get(route_name, '') + '?' + urllib.parse.urlencode(params)

    def _apply_video_info(self, li, info):
        """Apply video metadata using InfoTagVideo instead of deprecated setInfo."""
        if not info or not isinstance(info, dict):
            return
        try:
            tag = li.getVideoInfoTag()
            title = info.get('title')
            if title:
                tag.setTitle(title)
            duration = info.get('duration')
            if isinstance(duration, (int, float)):
                tag.setDuration(int(duration))
            elif isinstance(duration, str) and duration.isdigit():
                tag.setDuration(int(duration))
            resume = info.get('resume')
            resume_total = info.get('resume_total')
            if isinstance(resume, (int, float)) and resume_total is not None:
                tag.setResumePoint(int(resume), int(resume_total))
            total_time = info.get('total_time')
            if isinstance(total_time, (str, int, float)):
                tag.setTotalTime(int(total_time))
            plot = info.get('plot')
            if plot:
                tag.setPlot(plot)
            plotoutline = info.get('plotoutline')
            if plotoutline:
                tag.setPlotOutline(plotoutline)
            mpaa = info.get('mpaa')
            if mpaa:
                tag.setMpaa(mpaa)
            aired = info.get('aired')
            if aired:
                tag.setFirstAired(aired)
        except Exception:
            pass

    def _listitemify(self, item):
        """Convert a dict-based item into an xbmcgui.ListItem."""
        li = xbmcgui.ListItem(label=item.get('label', ''))
        thumb = item.get('thumbnail') or (item.get('properties') or {}).get('fanart_image')
        if thumb:
            li.setArt({'thumb': thumb})
        properties = item.get('properties')
        if isinstance(properties, dict) and properties:
            li.setProperties(properties)
        info = item.get('info')
        if info:
            self._apply_video_info(li, info)
        path = item.get('path')
        if path:
            li.setPath(str(path))
        return li

    def map_collection_to_playlist(self, collection):
        """Add items (list of dict items with 'path') to the video playlist."""
        # Empty playlist, otherwise requested video is present twice in the playlist
        pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        for item in collection or []:
            path = item.get('path')
            li = self._listitemify(item)
            try:
                pl.add(path, li)
            except Exception:
                xbmc.log(f"Could not add to playlist: {path}", xbmc.LOGWARNING)
        return pl

    def play_video(self, item):
        """Play a dictionary-based playable item with metadata."""
        if not isinstance(item, dict):
            return False
        path = item.get('path')
        if not path:
            return False
        li = self._listitemify(item)
        try:
            xbmc.Player().play(str(path), li)
            return True
        except Exception:
            return False

    def set_content(self, content):
        """Set the content type for the current directory (e.g., 'movies', 'tvshows')."""
        if self.handle is not None and content:
            try:
                xbmcplugin.setContent(self.handle, content)
            except Exception:
                pass

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
                    try:
                        path = item.get('path')
                        is_playable = item.get('is_playable', False)
                        li = self._listitemify(item)
                        ctx = item.get('context_menu')
                        if ctx:
                            try:
                                li.addContextMenuItems(ctx, replaceItems=False)
                            except Exception:
                                pass
                        xbmcplugin.addDirectoryItem(
                            handle=self.handle, url=path, listitem=li, isFolder=not is_playable)
                    except Exception as exc:
                        xbmc.log(f"Error rendering menu item: {exc}", xbmc.LOGWARNING)
                try:
                    xbmcplugin.endOfDirectory(self.handle)
                except Exception:
                    pass
            elif isinstance(result, dict) and result.get('path') and result.get('is_playable'):
                li = self._listitemify(result)
                xbmcplugin.setResolvedUrl(self.handle, True, li)


class NotificationMixin:
    """Notification helpers for addon UI messages."""

    def __init__(self, *args, **kwargs):
        self.addon = xbmcaddon.Addon()
        super().__init__(*args, **kwargs)

    def notify(self, msg, image=None, mtime=5000):
        """Show a notification message in Kodi."""
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
