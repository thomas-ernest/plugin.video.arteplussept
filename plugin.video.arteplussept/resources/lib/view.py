"""Manage views like home menu, dynamic menus, search, favorites..."""
import xbmc

from resources.lib import api
from resources.lib import hof
from resources.lib import settings as stg
from resources.lib import user
from resources.lib.mapper import mapper
from resources.lib.mapper.arteitem import ArteItem
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
            .build_item_live(settings.quality, '1'))
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


def build_mixed_collection(plugin, kind, collection_id, settings):
    """Build menu of content available in collection collection_id thanks to HBB TV API"""
    return [mapper.map_generic_item(plugin, item, settings.show_video_streams) for item in
            api.collection(kind, collection_id, settings.language)]


def build_video_streams(plugin, settings, program_id):
    """Build the menu with the audio streams available for content program_id"""
    item = api.video(program_id, settings.language)

    if item is None:
        raise RuntimeError('Video not found...')

    program_id = item.get('programId')
    kind = item.get('kind')

    return mapper.map_streams(
        plugin, item, api.streams(kind, program_id, settings.language), settings.quality)


def build_sibling_playlist(plugin, settings, program_id):
    """
    Return a pair with videos belonging to the same parent as program id
    e.g. other episodes of a same serie, videos around the same topic
    and the start program id of this collection i.e. program_id
    """
    parent_program = None
    # get parent of prefered kind first. for the moment TV_SERIES only
    for prefered_kind in ArteItem.PREFERED_KINDS:
        # pylint: disable=cell-var-from-loop
        parent_program = hof.find(
            lambda parent: api.is_of_kind(parent, prefered_kind),
            api.get_parent_collection(settings.language, program_id))
        if parent_program:
            break
    # if a parent was found, then return the list of kodi playable dict.
    if parent_program:
        sibling_arte_items = api.collection_with_last_viewed(
            settings.language, user.get_cached_token(plugin, settings.username, True),
            parent_program.get('kind'), parent_program.get('programId'))
        return mapper.map_collection_as_playlist(plugin, settings, sibling_arte_items, program_id)
    return None


def build_playlist_collection(plugin, settings, collection_id):
    """
    Build a playlist from artetv playlist api with multi lang streams
    """
    playlist = api.playlist_collection(settings.language, collection_id)
    collection = []
    first_prgm_id = None
    for pl_prgm in playlist.get('attributes', {}).get('items', {}):
        prgm_id = pl_prgm.get('providerId', None)
        if prgm_id:
            full_prgm = api.player_video(settings.language, prgm_id)
            streams = full_prgm.get('attributes', {}).get('streams', [])
            if len(streams) > 0:
                path = streams[0].get('url', None)
                if path:
                    prgm_attr = full_prgm.get('attributes', {}).get('metadata', {})
                    collection.append(
                        ArteTvVideoItem(plugin, prgm_attr).build_item(path, True)
                    )
                    if first_prgm_id is None:
                        first_prgm_id = prgm_id
    return {'collection': collection, 'start_program_id': first_prgm_id}


def build_collection_playlist(plugin, settings, kind, collection_id):
    """
    Return a pair with collection with collection_id
    and program id of the first element in the collection
    """
    return mapper.map_collection_as_playlist(
        plugin,
        settings,
        api.collection_with_last_viewed(
            settings.language,
            user.get_cached_token(plugin, settings.username, True),
            kind, collection_id))


def build_stream_url(plugin, settings, kind, program_id, audio_slot):
    """
    Return a playable menu item with metadata for the requested stream.
    """
    return mapper.map_video_as_playable_item(plugin, settings, kind, program_id, audio_slot)
