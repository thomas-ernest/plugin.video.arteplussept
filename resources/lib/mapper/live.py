"""
Module for ArteLiveItem depends on ArteTvVideoItem
Add specificities for live stream from Arte TV API.
"""

import html
# pylint: disable=import-error
from xbmcswift2 import actions
# the goal is to break/limit this dependency as much as possible
from resources.lib.mapper.arteitem import ArteTvVideoItem
from resources.lib.utils import PlayFrom


class ArteLiveItem(ArteTvVideoItem):
    """
    Arte Live is slightly different from standard item, because it is stream from Arte TV API only.
    It cannot be part of a playlist.
    Its label is prefixed with LIVE.
    """

    def format_title_and_subtitle(self):
        """Orange prefix LIVE for live stream"""
        meta = self.json_dict.get('attributes').get('metadata')
        title = meta.get('title')
        subtitle = meta.get('subtitle')
        label = f"[B][COLOR ffffa500]LIVE[/COLOR] - {html.unescape(title)}[/B]"
        # suffixes
        if subtitle:
            label += f" - {html.unescape(subtitle)}"
        return label

    def build_item_live(self, live_cache):
        """Return menu entry to watch live content from Arte TV API"""
        item = self.json_dict
        # Remove language at the end to match program id e.g. _fr, _de
        program_id = item.get('id')[:-3]
        attr = item.get('attributes')
        meta = attr.get('metadata')

        duration = meta.get('duration').get('seconds')

        fanart_url = ""
        thumbnail_url = ""
        if meta.get('images') and meta.get('images')[0] and meta.get('images')[0].get('url'):
            # Remove query param type=TEXT to avoid title embeded in image
            fanart_url = meta.get('images')[0].get('url').replace('?type=TEXT', '')
            thumbnail_url = fanart_url

        # set live streams in cache for play_live route to use it
        live_cache['live'] = attr.get('streams')

        # the route "play_live" starts the live directly (thanks to cached streams)
        # while the route "play" in context menu starts the program from the beginning
        return {
            'label': self.format_title_and_subtitle(),
            'path': self.plugin.url_for('play_live'),
            'thumbnail': thumbnail_url,
            'fanart': fanart_url,
            'is_playable': True,  # not show_video_streams
            'info_type': 'video',
            'info': {
                'title': meta.get('title'),
                'duration': duration,
                'plot': meta.get('description'),
                'playcount': '0',
            },
            'context_menu': [(
                self.plugin.addon.getLocalizedString(30010),
                actions.background(self.plugin.url_for(
                    'play_from', kind='SHOW', program_id=program_id, play_from=PlayFrom.CTX.value))
            )]
        }
