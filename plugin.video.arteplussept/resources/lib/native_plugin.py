"""Lightweight native Plugin replacement for xbmcswift2 routing/navigation.
This provides:
- Plugin.route(path, name=...) decorator to register handlers
- Plugin.run() to dispatch based on sys.argv
- Plugin.url_for(route_name, **kwargs) to build plugin URLs
- Minimal helpers: set_content, set_resolved_url, play_video, add_to_playlist, get_storage, finish

This is intentionally minimal and tailored to this addon to remove the xbmcswift2 routing dependency.
"""
import sys
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import json
import os
import time


class Plugin:
    def __init__(self):
        self.base_url = sys.argv[0]
        try:
            self.handle = int(sys.argv[1])
        except Exception:
            self.handle = None
        self.addon = xbmcaddon.Addon()
        # path to addon profile directory (special://profile/addon_data/<id>)
        try:
            self.storage_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        except Exception:
            # fallback to special://home/
            self.storage_path = xbmcvfs.translatePath('special://home/')
        # route name -> function
        self._routes = {}
        # simple in-memory storage per process
        self._storage = {}


    def route(self, path, name=None):
        """Decorator to register route handlers. """
        def decorator(func):
            route_name = name or func.__name__
            self._routes[route_name] = func
            return func
        return decorator

    def url_for(self, route_name, **kwargs):
        params = {'route': route_name}
        for k, v in kwargs.items():
            params[k] = v
        return self.base_url + '?' + urllib.parse.urlencode(params)

    def get_storage(self, key, TTL=None):
        """
        File-backed storage with TTL support (TTL in minutes).
        Returns a dict-like object that auto-saves to <storage_path>/storage/<key>.json
        when modified. If the stored value is older than TTL, storage is reset.
        """
        storage_dir = os.path.join(self.storage_path, 'storage')
        # ensure directory exists (prefer xbmcvfs, fallback to os)
        try:
            if not xbmcvfs.exists(storage_dir):
                xbmcvfs.mkdir(storage_dir)
        except Exception:
            try:
                os.makedirs(storage_dir, exist_ok=True)
            except Exception:
                # if neither method works, continue and attempts to read/write will fail later
                pass

        file_path = os.path.join(storage_dir, f"{key}.json")

        class FileStorageDict(dict):
            def __init__(self, path, initial):
                super().__init__(initial or {})
                self._path = path

            def _save(self):
                try:
                    payload = {'created': int(time.time()), 'value': dict(self)}
                    # write atomically is not guaranteed, but use xbmcvfs for compatibility
                    with xbmcvfs.File(self._path, 'w') as fh:
                        fh.write(json.dumps(payload))
                except Exception as e:
                    xbmc.log(f"Failed saving storage file {self._path}: {e}", xbmc.LOGWARNING)

            def __setitem__(self, k, v):
                super().__setitem__(k, v)
                self._save()

            def __delitem__(self, k):
                super().__delitem__(k)
                self._save()

            def clear(self):
                super().clear()
                self._save()

            def update(self, *args, **kwargs):
                super().update(*args, **kwargs)
                self._save()

            def pop(self, *args, **kwargs):
                val = super().pop(*args, **kwargs)
                self._save()
                return val

        # try to load existing data
        try:
            if xbmcvfs.exists(file_path):
                with xbmcvfs.File(file_path, 'r') as fh:
                    content = fh.read()
                if content:
                    data = json.loads(content)
                    created = int(data.get('created', 0))
                    value = data.get('value', {})
                    if TTL is not None:
                        # TTL is in minutes
                        if int(time.time()) - created > int(TTL) * 60:
                            value = {}
                    return FileStorageDict(file_path, value)
        except Exception as e:
            xbmc.log(f"Failed loading storage file {file_path}: {e}", xbmc.LOGWARNING)

        # no existing file or expired -> create and persist empty storage
        fsd = FileStorageDict(file_path, {})
        try:
            fsd._save()
        except Exception:
            pass
        return fsd

    def add_to_playlist(self, collection):
        """Add items (list of dict items with 'path') to the video playlist.
        Returns list of created xbmcgui.ListItem objects or []
        """
        pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        results = []
        for item in collection or []:
            path = item.get('path')
            li = xbmcgui.ListItem(label=item.get('label', ''))
            # optional art
            thumb = item.get('thumbnail') or (item.get('properties') or {}).get('fanart_image')
            if thumb:
                li.setArt({'thumb': thumb})
            # add info if present
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
            # if listitem is a dict with path, create ListItem
            if isinstance(listitem, dict):
                li = xbmcgui.ListItem(label=listitem.get('label', ''))
                path = listitem.get('path')
                xbmcplugin.setResolvedUrl(self.handle, True, li)
            else:
                xbmcplugin.setResolvedUrl(self.handle, True, listitem)
        return True

    def play_video(self, listitem):
        # for compatibility, call set_resolved_url
        return self.set_resolved_url(listitem)

    def finish(self, *args, **kwargs):
        # compatibility: return the argument so code that expects a return value still gets it
        if len(args) == 1 and not kwargs:
            return args[0]
        return None

    def set_content(self, content):
        if self.handle is not None and content:
            try:
                xbmcplugin.setContent(self.handle, content)
            except Exception:
                pass

    def set_setting(self, key, value):
        """Set an addon setting via xbmcaddon API. Returns True on success."""
        try:
            # xbmcaddon expects strings for settings
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

    def notify(self, msg, image=None, time=5000):
        # convenience wrapper used in addon code
        try:
            xbmcgui.Dialog().notification(self.addon.getAddonInfo('name'), msg, image, time)
        except Exception:
            xbmc.log(f"Notification: {msg}")

    def run(self):
        """Dispatch to registered route based on query param 'route'.
        If handler returns a list of dicts, render them as directory items.
        """
        # parse params
        params = {}
        if len(sys.argv) > 2 and sys.argv[2]:
            params = urllib.parse.parse_qs(sys.argv[2][1:])
            # flatten single-value lists
            params = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in params.items()}
        route = params.pop('route', None)
        # choose index if no route
        if route is None:
            route = 'index'
        handler = self._routes.get(route)
        if handler is None:
            xbmc.log(f"No handler for route '{route}'", xbmc.LOGERROR)
            return
        # call handler with params
        try:
            result = handler(**params)
        except TypeError:
            # try calling without kwargs if signature doesn't match
            result = handler()
        # if result is a list, render directory
        if isinstance(result, list) and self.handle is not None:
            for item in result:
                try:
                    label = item.get('label')
                    path = item.get('path')
                    is_playable = item.get('is_playable', False)
                    li = xbmcgui.ListItem(label)
                    thumb = item.get('thumbnail') or (item.get('properties') or {}).get('fanart_image')
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
                    xbmcplugin.addDirectoryItem(handle=self.handle, url=path, listitem=li, isFolder=(not is_playable))
                except Exception as e:
                    xbmc.log(f"Error rendering menu item: {e}", xbmc.LOGWARNING)
            try:
                xbmcplugin.endOfDirectory(self.handle)
            except Exception:
                pass
        # if result is a dict with path and is_playable True, resolve
        elif isinstance(result, dict) and result.get('path') and result.get('is_playable'):
            li = xbmcgui.ListItem(label=result.get('label', ''))
            xbmcplugin.setResolvedUrl(self.handle, True, li)
        # else nothing to do


# convenience single instance for modules that expect Plugin in the module scope
_default_plugin = Plugin()
def get_default_plugin():
    return _default_plugin

