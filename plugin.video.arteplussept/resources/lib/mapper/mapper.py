"""Map JSON API outputs into playable content and menus for Kodi"""
# pylint: disable=import-error
import xbmc
import xbmcgui
from resources.lib import api
from resources.lib import utils
from resources.lib.mapper.arteitem import ArteTvVideoItem
from resources.lib.mapper.artezone import ArteZone
from resources.lib.mapper.artefavorites import ArteFavorites
from resources.lib.mapper.artehistory import ArteHistory


def map_category_item(plugin, item, category_code):
    """Return menu entry to access a category content"""
    title = item.get('title')
    path = plugin.url_for(
        'sub_category_by_title',
        category_code=category_code,
        sub_category_title=utils.encode_string(title))

    li = xbmcgui.ListItem(label=title)
    li.setPath(path)
    li.setProperty('is_playable', 'False')
    return li


def map_collection_as_playlist(plugin, settings, arte_collection, req_start_program_id=None):
    """
    Map a collection from arte API to a list of items ready to build a playlist.
    Playlist item will be in the same order as arte_collection, if start_program_id
    is None, otherwise it starts from item with program id equals to start_program_id
    (and the same order).
    Return an empty list, if arte_collection is None or empty.
    """
    items_before_start = []
    items_after_start = []
    before_start = True
    if not arte_collection:
        return {'collection': [], 'start_program_id': None}

    # assume arte_collection[0] will be mapped successfully with map_video_as_playlist_item
    start_program_id = arte_collection[0].get('programId')
    for arte_item in arte_collection or []:

        # xbmc_item = map_video_as_playlist_item(plugin, settings, arte_item)
        xbmc_item = build_video_from_program(plugin, settings, arte_item)

        if xbmc_item is None:
            break

        # search for the start item until it is found once
        if before_start:
            if req_start_program_id is None:
                # start from the first element not fully viewed
                if ArteTvVideoItem(plugin, arte_item).get_progress() < 0.95:
                    before_start = False
                    start_program_id = arte_item.get('programId')
            else:
                # start from the requested element
                if req_start_program_id == arte_item.get('programId'):
                    before_start = False
                    start_program_id = req_start_program_id

        if before_start:
            items_before_start.append(xbmc_item)
        else:
            items_after_start.append(xbmc_item)
    return {
        'collection': items_after_start + items_before_start,
        'start_program_id': start_program_id
    }


def build_video_from_program(plugin, settings, prgm_id):
    """
    Build a full playable video with metadata from a single program.
    """
    if prgm_id:
        full_prgm = api.player_video(settings.language, prgm_id)
        streams = full_prgm.get('attributes', {}).get('streams', [])
        if len(streams) > 0:
            path = streams[0].get('url', None)
            if path:
                prgm_attr = full_prgm.get('attributes', {}).get('metadata', {})
                return ArteTvVideoItem(plugin, prgm_attr).build_item(path, True)
    return None


def map_zone_to_item(plugin, settings, zone):
    """Arte TV API page is split into zones. Map a 'zone' to menu item(s).
    Never use cache, because we cannot store ListItem in it"""
    menu_item = None
    title = zone.get('title')
    if get_authenticated_content_type(zone) == 'sso-favorites':
        menu_item = ArteFavorites(plugin, settings).build_item(title)
    elif get_authenticated_content_type(zone) == 'sso-personalzone':
        menu_item = ArteHistory(plugin, settings).build_item(title)
    elif zone.get('content') and zone.get('content').get('data'):
        menu_item = ArteZone(plugin, settings).build_item(zone)
#    elif zone.get('link'):
#        menu_item = map_api_categories_item(plugin, zone)
    else:
        xbmc.log(
            f"Ignore zone \"{title}\". No link. No content. Unknown id.",
            level=xbmc.LOGINFO)

    return menu_item


def get_authenticated_content_type(artetv_zone):
    """
    Return the value of artetv_zone.authenticatedContent.contentId or None.
    Known values are sso-personalzone and sso-favorites
    """
    if not isinstance(artetv_zone, dict):
        return None
    if not isinstance(artetv_zone.get('authenticatedContent'), dict):
        return None
    return artetv_zone.get('authenticatedContent', {}).get('contentId', None)
