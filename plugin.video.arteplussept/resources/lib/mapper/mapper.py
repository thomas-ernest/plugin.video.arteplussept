"""Map JSON API outputs into playable content and menus for Kodi"""
# pylint: disable=import-error
import xbmc
from resources.lib import api
from resources.lib.mapper.arteitem import ArteTvVideoItem
from resources.lib.mapper.artezone import ArteZone
from resources.lib.mapper.artefavorites import ArteFavorites
from resources.lib.mapper.artehistory import ArteHistory


def build_video_from_program(plugin, settings, prgm_id, col_id=None):
    """
    Build a full playable video with metadata from a single program.
    """
    path = None
    if prgm_id:
        full_prgm = api.player_video(settings.language, prgm_id)
        if col_id:
            path = build_path_for_menu(plugin, col_id, prgm_id)
        else:
            path = build_path_for_playlist(full_prgm)
    if path:
        prgm_attr = full_prgm.get('attributes', {}).get('metadata', {})
        return ArteTvVideoItem(plugin, prgm_attr).build_item(path, True)
    return None


def build_path_for_menu(plugin, col_id, prgm_id):
    """Build path to point to playing a program in a collection"""
    return plugin.url_for('play_collection_from', col_id=col_id, prgm_id=prgm_id, mpaa='Unknown')


def build_path_for_playlist(full_prgm):
    """Build path to a playable multi lang video"""
    path = ''
    streams = full_prgm.get('attributes', {}).get('streams', [])
    if len(streams) > 0:
        path = streams[0].get('url', None)
    return path


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
