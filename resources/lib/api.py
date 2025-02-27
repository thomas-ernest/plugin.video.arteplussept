"""Arte TV and HBB TV API communications - REST and authentication calls"""
from collections import OrderedDict
# pylint: disable=import-error
import requests
# pylint: disable=import-error
from xbmcswift2 import xbmc
from xbmcswift2.plugin import Plugin
from resources.lib import hof
from resources.lib import logger

_PLUGIN_NAME = Plugin().name
_PLUGIN_VERSION = Plugin().addon.getAddonInfo('version')
# Arte hbbtv - deprecated API since 2022 prefer Arte TV API
_HBBTV_URL = 'https://www.arte.tv/hbbtvv2/services/web/index.php'
_HBBTV_HEADERS = {
    'user-agent': f"{_PLUGIN_NAME}/{_PLUGIN_VERSION}"
}
_HBBTV_ENDPOINTS = {
    'category': '/EMAC/teasers/category/v2/{category_code}/{lang}',
    'collection': '/EMAC/teasers/collection/v2/{collection_id}/{lang}',
    # program details
    'video': '/OPA/v3/videos/{program_id}/{lang}',
    # program streams
    'streams': '/OPA/v3/streams/{program_id}/{kind}/{lang}'
}


# Arte TV API - Used on Arte TV website
_ARTETV_URL = 'https://api.arte.tv/api'
ARTETV_RPROXY_URL = 'https://arte.tv/api/rproxy'
_ARTETV_AUTH_URL = 'https://auth.arte.tv/ssologin'
ARTETV_ENDPOINTS = {
    # POST
    'token': '/sso/v3/token',
    # needs token in authorization header
    'get_favorites': '/sso/v3/favorites/{lang}?page={page}&limit={limit}',
    # PUT
    # needs token in authorization header
    'add_favorite': '/sso/v3/favorites',
    # DELETE
    # needs token in authorization header
    'remove_favorite': '/sso/v3/favorites/{program_id}',
    # PATCH empty payload
    # needs token in authorization header
    'purge_favorites': '/sso/v3/favorites/purge',
    # needs token in authorization header
    'get_last_viewed': '/sso/v3/lastvieweds/{lang}?page={page}&limit={limit}',
    # PUT
    # needs token in authorization header
    # payload {'programId':'110342-012-A','timecode':574} for 574s i.e. 9:34
    'sync_last_viewed': '/sso/v3/lastvieweds',
    # PATCH empty payload
    # needs token in authorization header
    'purge_last_viewed': '/sso/v3/lastvieweds/purge',
    # program_id can be 103520-000-A or LIVE
    'player': '/player/v2/config/{lang}/{program_id}',
    # rproxy
    'program': '/emac/v4/{lang}/web/programs/{program_id}',
    # rproxy
    # category=HOME, CIN, SER, SEARCH client=app, tv, web, orange, free
    'page': '/emac/v4/{lang}/{client}/pages/{category}/',
    # rproxy
    # zone_id=167d478a-b668-42a3-b88a-f01a436c7394...
    # keep path and url in a snigle place for readibility
    # page_id=SEARCH, HOME...
    'zone':
        '/emac/v4/{lang}/{client}/zones/{zone_id}/content?' +
        'abv=A&authorizedCountry={lang}&page={page}&pageId={page_id}&' +
        'query={query}&zoneIndexInPage=0',
    # not yet impl.
    # rproxy date=2023-01-17
    # 'guide_tv': '/emac/v3/{lang}/{client}/pages/TV_GUIDE/?day={DATE}',
    # auth api
    'custom_token': '/setCustomToken',
    # auth api
    'login': '/login',
}
ARTETV_HEADERS = {
    'user-agent': f"{_PLUGIN_NAME}/{_PLUGIN_VERSION}",
    # required to use token endpoint
    'authorization': 'I6k2z58YGO08P1X0E8A7VBOjDxr8Lecg',
    # required for Arte TV API. values like web, app, tv, orange, free
    # prefer client tv over web so that Arte adapt content to tv limiting links for instance
    'client': 'tv',
    'accept': 'application/json'
}
_API_KEY = '97598990-f0af-427b-893e-9da348d9f5a6'
_COOKIES = {
    'TCPID': '123261154911117061452',
    # pylint: disable=line-too-long
    'TC_PRIVACY': '1%40031%7C29%7C3445%40%40%401677322453596%2C1677322453596%2C1711018453596%40',
    'TC_PRIVACY_CENTER': None
}


def get_favorites(lang, tkn, page_idx, page_size=50):
    """Retrieve favorites from a personal account."""
    url = _ARTETV_URL + ARTETV_ENDPOINTS['get_favorites'].format(
        lang=lang, page=page_idx, limit=page_size)
    return _load_json_personal_content('artetv_getfavorites', url, tkn)


def add_favorite(tkn, program_id):
    """
    Add content program_id to user favorites.
    :return: HTTP status code.
    """
    url = _ARTETV_URL + ARTETV_ENDPOINTS['add_favorite']
    headers = _add_auth_token(tkn, ARTETV_HEADERS)
    data = {'programId': program_id}
    reply = requests.put(url, data=data, headers=headers, timeout=10)
    logger.log_json(reply, 'artetv_addfavorite')
    return reply.status_code


def remove_favorite(tkn, program_id):
    """
    Remove content program_id from user favorites.
    :return: HTTP status code.
    """
    url = _ARTETV_URL + ARTETV_ENDPOINTS['remove_favorite'].format(program_id=program_id)
    headers = _add_auth_token(tkn, ARTETV_HEADERS)
    reply = requests.delete(url, headers=headers, timeout=10)
    logger.log_json(reply, 'artetv_removefavorite')
    return reply.status_code


def purge_favorites(tkn):
    """Flush user favorites"""
    url = _ARTETV_URL + ARTETV_ENDPOINTS['purge_favorites']
    headers = _add_auth_token(tkn, ARTETV_HEADERS)
    reply = requests.patch(url, data={}, headers=headers, timeout=10)
    logger.log_json(reply, 'artetv_purgefavorites')
    return reply.status_code


def get_last_viewed(lang, tkn, page_idx, page_size=50):
    """Retrieve content recently watched by a user."""
    url = _ARTETV_URL + ARTETV_ENDPOINTS['get_last_viewed'].format(
        lang=lang, page=page_idx, limit=page_size)
    return _load_json_personal_content('artetv_lastviewed', url, tkn)


def get_last_viewed_all(lang, tkn):
    """
    Retrieve every content recently watched by a user, all pages.
    Never None. Empty list in the worst case
    """
    all_data = []
    next_page_idx = 1
    while next_page_idx:
        current_page = get_last_viewed(lang, tkn, next_page_idx)
        if current_page is not None and isinstance(current_page, dict):
            all_data = all_data + current_page.get('data', [])
        next_page_idx = _get_next_page(current_page)
    return all_data


def _get_next_page(last_viewed):
    """Return the next page idx or False, never None"""
    if last_viewed is None:
        return False
    if not isinstance(last_viewed.get('meta', False), dict):
        return False
    current_page = last_viewed.get('meta').get('page')
    if current_page < last_viewed.get('meta').get('pages'):
        return int(current_page) + 1
    return False


def sync_last_viewed(tkn, program_id, time):
    """
    Synchronize in arte profile the progress time of content being played.
    :return: HTTP status code.
    """
    url = _ARTETV_URL + ARTETV_ENDPOINTS['sync_last_viewed']
    headers = _add_auth_token(tkn, ARTETV_HEADERS)
    data = {'programId': program_id, 'timecode': time}
    reply = requests.put(url, data=data, headers=headers, timeout=10)
    logger.log_json(reply, 'artetv_synchlastviewed')
    return reply.status_code


def purge_last_viewed(tkn):
    """Flush user history"""
    url = _ARTETV_URL + ARTETV_ENDPOINTS['purge_last_viewed']
    headers = _add_auth_token(tkn, ARTETV_HEADERS)
    reply = requests.patch(url, data={}, headers=headers, timeout=10)
    logger.log_json(reply, 'artetv_purgelastviewed')
    return reply.status_code


def player_video(lang, program_id):
    """Get the info of content program_id from Arte TV API."""
    url = _ARTETV_URL + ARTETV_ENDPOINTS['player'].format(lang=lang, program_id=program_id)
    return _load_json_full_url('artetv_player', url, None).get('data', {})


def program_video(lang, program_id):
    """Get the info of content program_id from Arte TV API."""
    url = ARTETV_RPROXY_URL + ARTETV_ENDPOINTS['program'].format(lang=lang, program_id=program_id)
    return _load_json_full_url('artetv_program', url, None).get('value', {})


def get_parent_collection(lang, program_id):
    """
    Get parent collection of program program_id.
    Return an empty list, if nothing found.
    """
    artetv_program_stream = program_video(lang, program_id)
    if artetv_program_stream:
        for zone in artetv_program_stream.get('zones', []):
            if zone.get('content'):
                for data in zone.get('content').get('data'):
                    return data.get('parentCollections', [])
    return []


def is_of_kind(arte_item, kind):
    """Return true if arte_item is not None and of the kind provided as parameter"""
    return (arte_item and arte_item.get('kind') == kind) or False


def category(category_code, lang):
    """Get the info of category with category_code."""
    url = _HBBTV_ENDPOINTS['category'].format(category_code=category_code, lang=lang)
    return _load_json('hbbtv_category', url).get('category', {})


def collection(kind, collection_id, lang):
    """Get the info of collection collection_id"""
    url = _HBBTV_ENDPOINTS['collection'].format(
        kind=kind, collection_id=collection_id, lang=lang)
    sub_collections = _load_json('hbbtv_collection', url).get('subCollections', [])
    return hof.flat_map(
        lambda sub_collections: sub_collections.get('videos', []),
        sub_collections)


def collection_with_last_viewed(lang, tkn, kind, collection_id):
    """
    Get the info of collection collection_id and enhanced them with last_viewed details
    e.g. progress
    """
    collection_items = collection(kind, collection_id, lang)
    last_viewed_items = get_last_viewed_all(lang, tkn)
    # nothing to do
    if len(collection_items) < 1 or len(last_viewed_items) < 1:
        return collection_items
    # merge the 2 collection based on program id.
    last_viewed_map = {}
    for item in last_viewed_items:
        last_viewed_map[item.get('programId')] = item
    for idx, basic_item in enumerate(collection_items):
        if basic_item is not None and basic_item.get('programId') is not None:
            enhanced_item = last_viewed_map.get(basic_item.get('programId'))
            if enhanced_item is not None:
                collection_items[idx] = enhanced_item
    return collection_items


def video(program_id, lang):
    """Get the info of content program_id from HBB TV API."""
    url = _HBBTV_ENDPOINTS['video'].format(
        program_id=program_id, lang=lang)
    return _load_json('hbbtv_video', url).get('videos', [])[0]


def streams(kind, program_id, lang):
    """Get the stream info of content program_id."""
    url = _HBBTV_ENDPOINTS['streams'].format(
        kind=kind, program_id=program_id, lang=lang)
    return _load_json('hbbtv_streams', url).get('videoStreams', [])


def page_content(lang):
    """Get content to be display in a page. It can be a page for a category or the home page."""
    url = ARTETV_RPROXY_URL + ARTETV_ENDPOINTS['page'].format(
        lang=lang, category='HOME', client='tv')
    return _load_json_full_url('artetv_home', url, ARTETV_HEADERS).get('value', [])


def init_search(lang, query):
    """
    Initialize a search for content in Arte TV API.
    Search will be identified by zone id then.
    """
    url = ARTETV_RPROXY_URL + ARTETV_ENDPOINTS['page'].format(
        lang=lang, category='SEARCH', client='tv')
    params = {'page': '1', 'query': query}
    return _load_json_full_url('artetv_initsearch', url, ARTETV_HEADERS, params).get(
        'value', []).get('zones', [None])[0]


def get_search_page(lang, zone_id, page_idx, query):
    """
    Navigate in pages of a search identified by zone_id.
    """
    url = ARTETV_RPROXY_URL + ARTETV_ENDPOINTS['zone'].format(
        lang=lang, client='tv', zone_id=zone_id, page=page_idx, page_id='SEARCH', query=query)
    return _load_json_full_url('artetv_getsearchpage', url, ARTETV_HEADERS).get('value', [])


def get_zone_page(lang, zone_id, page_idx, page_id):
    """
    Navigate in pages of a zone identified by zone_id.
    """
    url = ARTETV_RPROXY_URL + ARTETV_ENDPOINTS['zone'].format(
        lang=lang, client='tv', zone_id=zone_id, page=page_idx, page_id=page_id, query='null')
    return _load_json_full_url('artetv_getsearchpage', url, ARTETV_HEADERS).get('value', [])


def _load_json(request_scope, path, headers=None):
    """Deprecated since 2022. Prefer building url on client side"""
    if headers is None:
        headers = _HBBTV_HEADERS
    url = _HBBTV_URL + path
    return _load_json_full_url(request_scope, url, headers)


def _load_json_full_url(request_scope, url, headers=None, params=None):
    if headers is None:
        headers = _HBBTV_HEADERS
    # https://requests.readthedocs.io/en/latest/
    reply = requests.get(url, headers=headers, params=params, timeout=10)
    logger.log_json(reply, request_scope)
    return reply.json(object_pairs_hook=OrderedDict)


def _load_json_personal_content(request_scope, url, tkn, hdrs=None):
    """Get a bearer token and add it in headers before sending the request"""
    if hdrs is None:
        hdrs = ARTETV_HEADERS
    headers = _add_auth_token(tkn, hdrs)
    if not headers:
        return None
    return _load_json_full_url(request_scope, url, headers)


# Get a bearer token and add it as HTTP header authorization
def _add_auth_token(tkn, hdrs):
    if not tkn:
        return None
    headers = hdrs.copy()
    headers['authorization'] = f"{tkn['token_type']} {tkn['access_token']}"
    # web client needed to reuse token. Otherwise API rejects with
    # {"error":"invalid_client","error_description":"Client not authorized"}
    headers['client'] = 'web'
    return headers


def get_and_persist_token_in_arte(plugin, username, password):
    """Log in user thanks to his/her settings and get a bearer token.
    Return None if:
        - any parameter is empty
        - silenty if both parameters are empty
        - with a notification if one is not empty
        - connection to arte tv failed"""

    tokens = authenticate_in_arte(plugin, username, password)
    # exit if authentication failed
    if not tokens:
        return None

    # try to persist token in arte to be allowed to reuse; otherwise token is one-shot
    if not persist_token_in_arte(plugin, tokens):
        return None

    # return persisted or unpersisted token anyway
    return tokens


def authenticate_in_arte(plugin, username='', password='', headers=None):
    """Return None if authentication failed and display an error notification
    Return arte reply with access and refresh tokens if authentication was successfull
    (i.e. status 200, no exception)"""
    if headers is None:
        headers = ARTETV_HEADERS
    # set client to web, because with tv get error client_invalid, error Client not authorized
    headers['client'] = 'web'

    url = _ARTETV_URL + ARTETV_ENDPOINTS['token']
    token_data = {
        'anonymous_token': None,
        'grant_type': 'password',
        'username': username,
        'password': password
    }
    xbmc.log(f"Try authenticating \"{username}\" to Arte TV")
    error = None
    reply = None
    try:
        # https://requests.readthedocs.io/en/latest/
        reply = requests.post(url, data=token_data, headers=headers, timeout=10)
        logger.log_json(reply, 'artetv_auth')
    except requests.exceptions.ConnectionError as err:
        # unable to auth. e.g.
        # HTTPSConnectionPool(host='api.arte.tv', port=443):
        # Max retries exceeded with url: /api/sso/v3/token
        error = err
    if error or not reply or reply.status_code != 200:
        err_dtls = str(error) if error else (reply.text if reply is not None else '')
        xbmc.log(f"Unable to authenticate to Arte TV : {err_dtls}", level=xbmc.LOGERROR)
        plugin.notify(msg=plugin.addon.getLocalizedString(30020), image='error')
        return None
    return reply.json(object_pairs_hook=OrderedDict)


def persist_token_in_arte(plugin, tokens, headers=None):
    """Calls the sequence of 2 services to be able to reuse authentication token
    Return True, if token is persisted, False otherwise.
    Notify the user with a warning if persistance failed.
    """
    if headers is None:
        headers = ARTETV_HEADERS
    # set client to web, because with tv get error client_invalid, error Client not authorized
    headers['client'] = 'web'

    # step 1/2 : get additional cookies for step 2.
    url = _ARTETV_AUTH_URL + ARTETV_ENDPOINTS['custom_token']
    params = {
        'shouldValidateAnonymous': False,
        'token': tokens['access_token'],
        'apikey': _API_KEY,
        'isrememberme': True
    }
    error = None
    cstm_tkn = None
    try:
        cstm_tkn = requests.get(url, params=params, headers=headers, cookies=_COOKIES, timeout=10)
        logger.log_json(cstm_tkn, 'artetv_customtoken')
    except requests.exceptions.ConnectionError as err:
        error = err
    if error or not cstm_tkn or cstm_tkn.status_code != 200:
        err_dtls = str(error) if error else (cstm_tkn.text if cstm_tkn is not None else '')
        xbmc.log(
            f"Unable to persist Arte TV token {tokens['access_token']}. Step 1/2: {err_dtls}",
            level=xbmc.LOGERROR)
        plugin.notify(msg=plugin.addon.getLocalizedString(30020), image='warning')
        return False

    # step 2/2 : persist / remember token so that it can be reused
    url = _ARTETV_AUTH_URL + ARTETV_ENDPOINTS['login']
    params = {'shouldValidateAnonymous': 'false', 'apikey': _API_KEY}
    cookies = hof.merge_dicts(_COOKIES, cstm_tkn.cookies)
    login = None
    try:
        login = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=10)
        logger.log_json(login, 'artetv_login')
    except requests.exceptions.ConnectionError as err:
        error = err
    if error or not login or login.status_code != 200:
        err_dtls = str(error) if error else (login.text if login is not None else '')
        xbmc.log(
            f"Unable to persist Arte TV token {tokens['access_token']}. Step 2/2: {err_dtls}",
            level=xbmc.LOGERROR)
        plugin.notify(msg=plugin.addon.getLocalizedString(30020), image='warning')
        return False

    return True
