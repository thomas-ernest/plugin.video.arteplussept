"""Utility methods for:
- strings encoding/decoding for URL usage
- age restrictions/MPAA mapping qnd warnings
"""
import urllib.parse
from enum import Enum
import xbmcgui


class PlayFrom(Enum):
    """Define from where the play request is initiated"""
    ITM = 'item'
    LST = 'playlist'
    CTX = 'context_menu'


def encode_string(string):
    """Return escaped string to be used as URL. More details in
    https://docs.python.org/3/library/urllib.parse.html#urllib.parse.quote_plus"""
    return urllib.parse.quote_plus(string, encoding='utf-8', errors='replace')


def decode_string(string):
    """Return unescaped string to be human readable. More details in
    https://docs.python.org/3/library/urllib.parse.html#urllib.parse.unquote_plus"""
    return urllib.parse.unquote_plus(string, encoding='utf-8', errors='replace')


def mpaa_from_age(age):
    """Map an integer age restriction to an MPAA rating string.

    Returns 'Unknown' when mapping cannot be determined.
    """
    mpaa = 'Unknown'
    if isinstance(age, int):
        if age == 0:
            mpaa = 'G'
        elif 0 < age < 12:
            mpaa = 'PG'
        elif 12 <= age < 16:
            mpaa = 'PG-13'
        elif 16 <= age < 18:
            mpaa = 'R'
        elif 18 <= age:
            mpaa = 'NC-17'
    return mpaa


def warn_if_age_restricted(plugin, mpaa):
    """Return True if the MPAA rating requires a warning
    i.e. when MPAA is in ('PG-13', 'R', 'NC-17')
    and notify with a warning translated message.

    Parameters:
    - plugin: the xbmcswift2 Plugin instance used to translate and display the
      notification. If falsy, only the boolean result is returned.
    - mpaa: MPAA rating string to evaluate.
    """
    restricted = bool(mpaa) and mpaa in ('PG-13', 'R', 'NC-17')
    if restricted and plugin:
        msg = plugin.addon.getLocalizedString(30055).format(label=mpaa)
        plugin.notify(msg=msg, image='warning')
    return restricted


def getDictFromInfoTagVideo(li):
    """Extract common video InfoTag fields from a ListItem's VideoInfoTag into a dict.

    This probes the tag for known getters and only calls them when present,
    avoiding broad exception handling.
    """
    if not hasattr(li, 'getVideoInfoTag'):
        return None

    tag = li.getVideoInfoTag()
    if not tag:
        return None

    info = {}

    if hasattr(tag, 'getTitle'):
        info['title'] = tag.getTitle()
    if hasattr(tag, 'getPlot'):
        info['plot'] = tag.getPlot()
    if hasattr(tag, 'getPlotOutline'):
        info['plotoutline'] = tag.getPlotOutline()
    if hasattr(tag, 'getMpaa'):
        info['mpaa'] = tag.getMpaa()
    if hasattr(tag, 'getDuration'):
        info['duration'] = tag.getDuration()
    if hasattr(tag, 'getFirstAiredAsW3C'):
        info['firstairedasw3c'] = tag.getFirstAiredAsW3C()
    if hasattr(tag, 'getGenres'):
        genres = tag.getGenres()
        info['genres'] = list(genres) if genres is not None else None
    if hasattr(tag, 'getDirectors'):
        directors = tag.getDirectors()
        info['directors'] = list(directors) if directors is not None else None
    if hasattr(tag, 'getWriters'):
        writers = tag.getWriters()
        info['writers'] = list(writers) if writers is not None else None
    if hasattr(tag, 'getCountries'):
        countries = tag.getCountries()
        info['countries'] = list(countries) if countries is not None else None
    if hasattr(tag, 'getYear'):
        info['year'] = tag.getYear()

    return info


def getInfoTagVideoFromDict(info_dict, li):
    """
    Apply a previously-serialized video info dict back onto a ListItem.
    """
    if not info_dict:
        return

    if hasattr(li, 'getVideoInfoTag'):
        tag = li.getVideoInfoTag()
        if not tag:
            return

        # Map known keys to setters when present
        if 'title' in info_dict and hasattr(tag, 'setTitle'):
            tag.setTitle(info_dict.get('title'))
        if 'plot' in info_dict and hasattr(tag, 'setPlot'):
            tag.setPlot(info_dict.get('plot'))
        if 'plotoutline' in info_dict and hasattr(tag, 'setPlotOutline'):
            tag.setPlotOutline(info_dict.get('plotoutline'))
        if 'mpaa' in info_dict and hasattr(tag, 'setMpaa'):
            tag.setMpaa(info_dict.get('mpaa'))
        if 'duration' in info_dict and hasattr(tag, 'setDuration'):
            tag.setDuration(info_dict.get('duration'))
        if 'firstairedasw3c' in info_dict:
            tag.setFirstAired(info_dict.get('firstairedasw3c'))
        if 'genres' in info_dict and hasattr(tag, 'setGenres'):
            tag.setGenres(info_dict.get('genres'))
        if 'directors' in info_dict and hasattr(tag, 'setDirectors'):
            tag.setDirectors(info_dict.get('directors'))
        if 'writers' in info_dict and hasattr(tag, 'setWriters'):
            tag.setWriters(info_dict.get('writers'))
        if 'countries' in info_dict and hasattr(tag, 'setCountries'):
            tag.setCountries(info_dict.get('countries'))
        if 'year' in info_dict and hasattr(tag, 'setYear'):
            tag.setYear(info_dict.get('year'))

        return


def getDictFromListItem(li):
    # Serialize an xbmcgui.ListItem into a plain dict so it can be
    # JSON-serialized / persisted. Be defensive: not all ListItem
    # implementations expose the same getter methods, so wrap calls.
    dict = {}
    dict['label'] = li.getLabel()
    dict['path'] = li.getPath()
    dict['art'] = {}
    for art_key in ['thumb', 'fanart']:
        dict['art'][art_key] = li.getArt(art_key)
    props = {}
    if hasattr(li, 'getProperties'):
        props = li.getProperties()
    else:
        # fall back to probing a set of commonly used property keys
        if hasattr(li, 'getProperty'):
            for key in ('is_playable', 'StartOffset', 'StartPercent'):
                val = li.getProperty(key)
                if val is not None and val != '':
                    props[key] = val
    dict['properties'] = props

    # info labels (metadata)
    if hasattr(li, 'getInfoLabels') and li.getInfoLabels():
        dict['info'] = li.getInfoLabels()

    # video InfoTag (detailed metadata) when available
    dict['video_info_tag'] = getDictFromInfoTagVideo(li)

    return dict


def getListItemFromDict(item_dict):
    # Accept the dict previously produced by getDictFromListItem and
    # recreate an xbmcgui.ListItem. Use defensive calls for compatibility.
    data = item_dict or {}
    label = data.get('label') or ''
    li = xbmcgui.ListItem(label)
    path = data.get('path')
    if path:
        li.setPath(str(path))
    art = data.get('art')
    if isinstance(art, dict):
        li.setArt(art)

    # properties
    props = data.get('properties') or {}
    if props:
        if hasattr(li, 'setProperties'):
            li.setProperties(props)
        else:
            for k, v in props.items():
                li.setProperty(k, str(v))

    # apply video InfoTag data if present
    video_info = data.get('video_info_tag')
    if video_info:
        getInfoTagVideoFromDict(video_info, li)

    return li


def getDictFromListItemInList(lli):
    return [getDictFromListItem(li) for li in lli]


def getListItemFromDictInList(ldict):
    return [getListItemFromDict(idict) for idict in ldict]
