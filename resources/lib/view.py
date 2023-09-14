"""Manage views like home menu, dynamic menus, search, favorites..."""
# pylint: disable=import-error
from xbmcswift2 import xbmc
from xbmcswift2 import xbmcvfs

from resources.lib.mapper.arteitem import ArteItem
from resources.lib.mapper.live import ArteLiveItem
from resources.lib.mapper.arteitem import ArteVideoItem
from resources.lib.mapper.artesearch import ArteSearch
from resources.lib import api
from resources.lib import hof
from resources.lib.mapper import mapper
from resources.lib import settings as stg
from resources.lib import user
from resources.lib import m3u8
from os.path import join as OSPJoin


def build_home_page(plugin, settings, cached_categories):
    """Display home menu based on fixed entries and then content from API home page"""
    addon_menu = [
        ArteSearch(plugin, settings).build_item()
    ]
    try:
        addon_menu.append(
            ArteLiveItem(plugin, api.player_video(settings.language, 'LIVE'))
            .build_item_live(settings.quality, '1'))
    # pylint: disable=broad-exception-caught
    # Could be improve. possible exceptions are limited to auth. errors
    except Exception as error:
        xbmc.log("Unable to build live stream item with " +
                 f"lang:{settings.language} quality:{settings.quality} " +
                 f"because \"{str(error)}\"")

    arte_home = api.page_content(settings.language)
    for zone in arte_home.get('zones'):
        menu_item = mapper.map_zone_to_item(plugin, settings, zone, cached_categories)
        if menu_item:
            addon_menu.append(menu_item)
    return addon_menu


def build_api_category(plugin, category_code, settings):
    """Build the menu for a category that needs an api call"""
    category = [mapper.map_category_item(plugin, item, category_code) for item in
                api.category(category_code, settings.language)]

    return category


def get_cached_category(zone_id, cached_categories):
    """Return the menu for a category that is stored
    in cache from previous api call like home page"""
    return cached_categories[zone_id]


def mark_as_watched(plugin, usr, program_id, label):
    """
    Get program duration and synch progress with total duration
    in order to mark a program as watched
    """
    status = -1
    try:
        program_info = api.player_video(stg.languages[0], program_id)
        total_time = program_info.get('attributes').get('metadata').get('duration').get('seconds')
        status = api.sync_last_viewed(user.get_cached_token(plugin, usr), program_id, total_time)
    # pylint: disable=broad-exception-caught
    except Exception as excp:
        xbmc.log(f" exception caught :{str(excp)}")

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


def build_multilang_video(plugin, settings, program_id, duration):
    """Build the menu with the audio streams available for content program_id"""
    item = api.player_video(settings.language, program_id)

    base_url = ""
    video = None
    audios = {}
    for stream in item.get('attributes', []).get('streams', []):
        lang = stream['versions'][0]['eStat']['ml5']
        base_url = stream['url'].rsplit('/', 1)[0]
        m3u = m3u8.load(stream['url'])
        for playlist in m3u.playlists:
            info = playlist.stream_info
            if info.resolution == (1280, 720) and info.frame_rate == 25:
                video = playlist.uri
            for media in playlist.media:
                if media.type == 'AUDIO':
                    if audios.get(lang, None) is None:
                        audios[lang] = {}
                    audios[lang][media.language] = media.uri
    print('result=', "base=", base_url, "video=", video, "audios=", audios)

    vid_m3u = save_stream_m3u(plugin, program_id, "vid", build_mp4_url(base_url, video), duration)
    aud_m3u = {}
    for lang, url in build_audio_urls(base_url, audios).items():
        aud_m3u[lang] = save_stream_m3u(plugin, program_id, lang, url, duration)

    main_m3u_filename = save_main_m3u(plugin, program_id, vid_m3u, aud_m3u, duration)
    main_m3u_path = OSPJoin(plugin.storage_path, main_m3u_filename)

    video_item = ArteVideoItem(plugin, item.get('attributes', {}).get('metadata', None))
    return video_item._build_item(main_m3u_path, True)
#    return {'path': main_m3u_path}

def build_mp4_url(base_url, video):
    m3u_url = f"{base_url}/{video}"
    base_video_url = m3u_url.rsplit('/', 1)[0]
    video_m3u = m3u8.load(m3u_url)
    # sinlge video file expected (even if referenced multiple times)
    mp4_url = f"{base_video_url}/{video_m3u.files[0]}"
    return mp4_url

def build_audio_urls(base_url, audios):
    result = {}
    for lang_and_url in audios.values():
        lang = list(lang_and_url.keys())[0]
        m3u_path = list(lang_and_url.values())[0]
        m3u_url = f"{base_url}/{m3u_path}"
        base_audio_url = m3u_url.rsplit('/', 1)[0]
        audio_m3u = m3u8.load(m3u_url)
        result[lang]=f"{base_audio_url}/{audio_m3u.files[0]}"
    return result

def save_stream_m3u(plugin, program_id, suffix, url, duration):
    m3u_filename = f"{program_id}_{suffix}.m3u8"
    m3u_path = OSPJoin(plugin.storage_path, m3u_filename)
    with xbmcvfs.File(m3u_path, 'w') as m3u_file:
        m3u_file.write('#EXTM3U\n')
        #if suffix == "vid":
        m3u_file.write(f"#EXT-X-TARGETDURATION:{duration}\n")
        #    m3u_file.write('#EXT-X-VERSION:7\n')
        #    m3u_file.write('#EXT-X-MEDIA-SEQUENCE:1\n')
# not supported            m3u_file.write("#EXT-X-PLAYLIST-TYPE:VOD")
        m3u_file.write(f"#EXTINF:{duration}.0,\n")
        m3u_file.write(f"{url}\n")
        #m3u_file.write("#EXT-X-ENDLIST")

    return m3u_filename

def save_main_m3u(plugin, program_id, vid_m3u, aud_m3u, duration):
    m3u_filename = f"{program_id}_main.m3u8"
    m3u_path = OSPJoin(plugin.storage_path, m3u_filename)
    with xbmcvfs.File(m3u_path, 'w') as m3u_file:
        m3u_file.write('#EXTM3U\n')
        m3u_file.write('#EXT-X-VERSION:4\n')
        m3u_file.write('#EXT-X-PLAYLIST-TYPE:VOD\n')
        m3u_file.write(f"#EXT-X-TARGETDURATION:{duration}\n")
        m3u_file.write('#EXT-X-MEDIA-SEQUENCE:0\n')
        m3u_file.write('#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=4959904,AVERAGE-BANDWIDTH=2351104,VIDEO-RANGE=SDR,CODECS="avc1.4d401f,mp4a.40.2",RESOLUTION=1280x720,FRAME-RATE=25.000,AUDIO="lang"\n')
        m3u_file.write(f"{vid_m3u}\n")
        default = True
        for lang in aud_m3u:
            m3u_file.write(f"#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID=\"lang\",LANGUAGE=\"{lang}\",NAME=\"{lang}\",AUTOSELECT=YES,DEFAULT={'YES' if default == True else 'NO'},URI=\"{aud_m3u[lang]}\"\n")
            default = False
        m3u_file.write("#EXT-X-ENDLIST")
    return m3u_filename

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
        return mapper.map_collection_as_playlist(sibling_arte_items, program_id)
    return None


def build_collection_playlist(plugin, settings, kind, collection_id):
    """
    Return a pair with collection with collection_id
    and program id of the first element in the collection
    """
    return mapper.map_collection_as_playlist(plugin, api.collection_with_last_viewed(
        settings.language,
        user.get_cached_token(plugin, settings.username, True),
        kind, collection_id))


def build_stream_url(plugin, kind, program_id, audio_slot, settings):
    """
    Return URL to stream content.
    If the content is not available, it tries to return a related trailer or teaser.
    """
    # first try with content
    program_stream = api.streams(kind, program_id, settings.language)
    if program_stream:
        return mapper.map_playable(
            program_stream, settings.quality, audio_slot, mapper.match_hbbtv)
    # second try to fallback clip. It allows to display a trailer,
    # when a documentary is not available anymore like on arte tv website
    clip_stream = api.streams('CLIP', program_id, settings.language)
    if clip_stream:
        return mapper.map_playable(
            clip_stream, settings.quality, audio_slot, mapper.match_hbbtv)
    # otherwise raise the error
    msg = plugin.addon.getLocalizedString(30029)
    plugin.notify(msg=msg.format(strm=program_id, ln=settings.language), image='error')
    return None
