"""Utilities to write log files with API and Kodi display traces."""

import json
from os.path import join as OSPJoin
from datetime import datetime
# pylint: disable=import-error
from xbmcswift2 import Plugin
# pylint: disable=import-error
from xbmcswift2 import xbmcvfs
from . import settings


def log_json(reply, log_suffix):
    """save request and response in reply into a file
    with file name containing log_suffix in addon user data
    if loglevel settings is set to API.
    :param reply Python requests library object with every information to log
    :param log_suffix string to be used in log file name along current date and time
    """
    plugin = Plugin()
    msettings = settings.Settings(plugin)
    if reply is None or not msettings.should_log('API'):
        return

    base_path = plugin.storage_path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
    log_path = OSPJoin(base_path, f"{timestamp}_{log_suffix}-api.json")
    reqhdrs = format_headers(reply.request.headers)
    reshdrs = format_headers(reply.headers)
    with xbmcvfs.File(log_path, 'w') as log_file:
        log_file.write("---------------- request ----------------\n")
        log_file.write(f"{reply.request.method} {reply.request.url}\n")
        log_file.write(f"{reqhdrs}\n")
        log_file.write(f"payload : {reply.request.body}\n")
        log_file.write("---------------- response ----------------\n")
        log_file.write(f"{reply.status_code} {reply.reason} {reply.url}\n")
        log_file.write(f"{reshdrs}\n")
        log_file.write(f"payload : {reply.text}")


def log_xbmc(payload, log_suffix):
    """Serialize xbmc objects and listitems as JSON into addon storage."""
    plugin = Plugin()
    msettings = settings.Settings(plugin)
    if payload is None or not msettings.should_log('DISPLAY'):
        return

    base_path = plugin.storage_path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
    log_path = OSPJoin(base_path, f"{timestamp}_{log_suffix}-xbmc.json")
    with xbmcvfs.File(log_path, 'w') as log_file:
        payload_json = json.dumps(
            to_jsonable(payload), indent=2, sort_keys=True, ensure_ascii=False)
        log_file.write(payload_json)


def to_jsonable(payload):
    """Recursively convert native Python values and Kodi objects to JSON-safe data."""
    if payload is None or isinstance(payload, (str, int, float, bool)):
        return payload
    if isinstance(payload, (list, tuple)):
        return [to_jsonable(item) for item in payload]
    if isinstance(payload, dict):
        return {str(key): to_jsonable(value) for key, value in payload.items()}
    if isinstance(payload, bytes):
        return payload.decode('utf-8', 'replace')

    data = {}
    if hasattr(payload, '__dict__'):
        for attr_name, attr_value in vars(payload).items():
            if attr_name.startswith('_') or callable(attr_value):
                continue
            data[attr_name] = to_jsonable(attr_value)

    if not data:
        data = {'__repr__': repr(payload)}

    return {
        '__type__': f"{payload.__class__.__module__}.{payload.__class__.__name__}",
        **data,
    }


def format_headers(headers):
    """Map headers into a readable string to be logged."""
    return '\n'.join(f'{k}: {v}' for k, v in headers.items())
