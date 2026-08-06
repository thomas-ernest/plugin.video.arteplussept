"""Add-on settings"""

import dataclasses

languages = ['fr', 'de', 'en', 'es', 'pl', 'it', 'ro']
# though misleqding the below mapping is correct e.g. SQ is High Quality 720p
# dict keys must be in same order as in settings.xml
quality_map = {'Low': 'HQ', 'Medium': 'EQ', 'High': 'SQ'}
loglevel = {'DEFAULT': 'DEFAULT', 'API': 'API', 'DISPLAY': 'DISPLAY', 'API+DISPLAY': 'API+DISPLAY'}


@dataclasses.dataclass
class Settings:
    """Add-on settings"""
    def __init__(self, plugin):
        # Language used to query arte api
        # defaults to fr
        lang_idx = plugin.addon.getSettingInt('lang') or 0
        self.language = languages[lang_idx]
        # Quality of the videos
        # defaults to High, SQ, 720p
        quality_key_idx = plugin.addon.getSettingInt('quality') or 2
        self.quality = quality_map[list(quality_map.keys())[quality_key_idx]]
        # Should the plugin display all available streams for videos?
        # defaults to False
        self.show_video_streams = plugin.addon.getSettingBool(
            'show_video_streams') or False
        # Arte TV user name
        # defaults to empty string to return false with if not str
        self.username = plugin.addon.getSetting(
            'user_email') or ""
        # Enable additional logs managed by plugin: API and display object traces
        loglevel_key_idx = plugin.addon.getSettingInt('loglevel') or 0
        self.loglevel = loglevel[list(loglevel.keys())[loglevel_key_idx]]

    def should_log(self, log_type):
        """Return True when the configured loglevel includes the requested log type."""
        current_loglevel = self.loglevel

        if log_type == 'API':
            return current_loglevel in {loglevel['API'], loglevel['API+DISPLAY']}
        if log_type == 'DISPLAY':
            return current_loglevel in {loglevel['DISPLAY'], loglevel['API+DISPLAY']}
        # not current_loglevel or current_loglevel == loglevel['DEFAULT']
        return False
