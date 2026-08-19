"""Manage views like home menu, dynamic menus, search, favorites..."""
# pylint: disable=import-error
import xbmc

from resources.lib import api
from resources.lib import settings as stg
from resources.lib import user
from resources.lib.mapper import mapper
from resources.lib.mapper.arteitem import ArteTvVideoItem
from resources.lib.mapper.arteliveitem import ArteLiveItem
from resources.lib.mapper.artesearch import ArteSearch
from resources.lib.mapper.artezone import ArteZone


def build_home_page(plugin, settings):
    """Display home menu based on fixed entries and then content from API home page"""
    addon_menu = [
        ArteSearch(plugin, settings).build_item()
    ]
    try:
        addon_menu.append(
            ArteLiveItem(plugin, api.player_video(settings.language, 'LIVE'))
            .build_item_live())
    # pylint: disable=broad-exception-caught
    except Exception as error:
        xbmc.log("Unable to build live stream item with " +
                 f"lang:{settings.language} quality:{settings.quality} " +
                 f"because \"{str(error)}\"",
                 level=xbmc.LOGERROR)

    try:
        arte_home = api.page_content(settings.language)
        for zone in arte_home.get('zones'):
            menu_item = mapper.map_zone_to_item(plugin, settings, zone)
            if menu_item:
                addon_menu.append(menu_item)
    # pylint: disable=broad-exception-caught
    except Exception as error:
        xbmc.log("Unable to build home items with " +
                 f"lang:{settings.language} quality:{settings.quality} " +
                 f"because \"{str(error)}\"",
                 level=xbmc.LOGERROR)

    return addon_menu


def build_page(plugin, settings, category):
    """
    Build a page for a category like SER, CIN, DOR...
    A page is a list of zones.
    To be extended to HOME.
    """
    page = api.page_content(settings.language, category)
    page_menu = []
    for zone in page.get('zones', []):
        page_item = ArteZone(plugin, settings).build_item(zone)
        if page_item:
            page_menu.append(page_item)
    return page_menu


def mark_as_watched(plugin, usr, program_id, label):
    """
    Get program duration and synch progress with total duration
    in order to mark a program as watched
    """
    status = -1
    program_info = api.player_video(stg.languages[0], program_id)
    total_time = program_info.get('attributes').get('metadata').get('duration').get('seconds')
    auth_token = user.get_cached_token(plugin, usr)
    if auth_token:
        status = api.sync_last_viewed(auth_token, program_id, total_time)
        if 200 == status:
            msg = plugin.addon.getLocalizedString(30036).format(label=label)
            plugin.notify(msg=msg, image='info')
        else:
            msg = plugin.addon.getLocalizedString(30037).format(label=label)
            plugin.notify(msg=msg, image='error')


def build_sibling_playlist_from_program(plugin, settings, program_id):
    """
    Return a pair with videos belonging to the same parent as program id
    e.g. other episodes of a same serie, videos around the same topic
    and the start program id of this collection i.e. program_id
    """
    sibling_collection_id = None
    # get associated collection from arte tv item stats
    prgm = api.player_video(settings.language, program_id)
    if prgm:
        prgm_push = prgm.get('attributes', {}).get('stats', {}).get('push', {})
        assoc_collects = prgm_push.get('associatedCollection', [])
        if len(assoc_collects) > 0:
            for ac in assoc_collects:
                if isinstance(ac, str) and ac.startswith(("RC-", "PL-")):
                    sibling_collection_id = ac

    # if a parent was found, then return the list of kodi playable dict.
    playlist = None
    if sibling_collection_id:
        playlist = build_playlist_from_collection(plugin, settings, sibling_collection_id)
        if playlist:
            playlist['start_program_id'] = program_id
    return playlist


def build_menu_from_collection(plugin, settings, collection_id):
    """
    Build a playlist from artetv playlist api with multi lang streams
    """
    playlist = api.playlist_collection(settings.language, collection_id)
    menu = []
    for pl_prgm in playlist.get('attributes', {}).get('items', {}):
        prgm_id = pl_prgm.get('providerId', None)
        if prgm_id:
            path = plugin.url_for('play', program_id=prgm_id, mpaa='Unknown')
            li = ArteTvVideoItem(plugin, pl_prgm).build_item(path, True)
            if li:
                menu.append(li)
    return menu


def build_playlist_from_collection(plugin, settings, collection_id):
    """
    Build a playlist from artetv playlist api with multi lang streams
    """
    playlist = api.playlist_collection(settings.language, collection_id)
    collection = []
    first_prgm_id = None
    for pl_prgm in playlist.get('attributes', {}).get('items', {}):
        prgm_id = pl_prgm.get('providerId', None)
        if prgm_id:
            prgm_itm = mapper.build_video_from_program(plugin, settings, prgm_id)
            if prgm_itm:
                collection.append(prgm_itm)
                if first_prgm_id is None:
                    first_prgm_id = prgm_id
    return {'collection': collection, 'start_program_id': first_prgm_id}


def build_playable_playlist(playlist):
    """
    Convert a list of listitem into a playable video playlist
    """
    # Empty playlist, otherwise requested video is present twice in the playlist
    xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    for item in playlist or []:
        pl.add(item.getPath(), item)
    return pl


def build_video_from_program(plugin, settings, program_id):
    """
    Return a playable menu item with metadata for the requested stream.
    """
    return mapper.build_video_from_program(plugin, settings, program_id)
