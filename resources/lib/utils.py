"""Utility methods mainly to format strings and manipulate date"""
import urllib.parse
from enum import Enum


class DisplayType(Enum):
    """Define program display types for Arte content into Kodi menu"""
    COL = 'collection'
    ITM = 'item'


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
