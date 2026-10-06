"""Tests for best-effort user ID lookup in the home route."""
from unittest.mock import Mock
import importlib
import requests
import pytest


@pytest.fixture
def my_plugin_module(monkeypatch):
    """Import the add-on module with valid Kodi settings defaults."""
    # pylint: disable=import-outside-toplevel
    import xbmcaddon

    addon = Mock()
    addon.getSettingInt.return_value = 0
    addon.getSettingString.return_value = ''
    addon.getSettingBool.return_value = False
    monkeypatch.setattr(xbmcaddon, 'Addon', lambda: addon)
    return importlib.import_module('resources.lib.plugin')


@pytest.mark.parametrize(
    'error',
    [
        requests.exceptions.ConnectionError('offline'),
        ValueError('invalid JSON'),
    ],
)
def test_user_id_lookup_failure_does_not_block_home_menu(monkeypatch, error):
    """A failed profile request leaves the cached token intact and logs a warning."""
    token = {'access_token': 'cached-token'}
    monkeypatch.setattr(my_plugin_module.settings, 'username', 'user@example.test')
    monkeypatch.setattr(
        my_plugin_module.user,
        'get_cached_token',
        lambda *_args: token,
    )
    monkeypatch.setattr(
        my_plugin_module.api,
        'get_personal_data',
        lambda _token: _raise_error(error),
    )
    stored_tokens = []
    monkeypatch.setattr(
        my_plugin_module.user,
        'set_cached_token',
        lambda *_args: stored_tokens.append(True),
    )

    # Need to access the private method to test it
    # pylint: disable=protected-access
    my_plugin_module._attach_user_id_to_token()

    assert 'user_id' not in token
    assert not stored_tokens
    my_plugin_module.xbmc.log.assert_called_with(
        f'Unable to retrieve Arte userId; continuing without it: {error}',
        level=my_plugin_module.xbmc.LOGWARNING
    )


def _raise_error(error):
    raise error


def test_user_id_lookup_attaches_successful_result(monkeypatch):
    """A successful profile lookup still caches the user ID."""
    token = {'access_token': 'cached-token'}
    monkeypatch.setattr(my_plugin_module.settings, 'username', 'user@example.test')
    monkeypatch.setattr(
        my_plugin_module.user,
        'get_cached_token',
        lambda *_args: token,
    )
    monkeypatch.setattr(
        my_plugin_module.api,
        'get_personal_data',
        lambda _token: {'userId': 'arte-user-id'},
    )
    stored_tokens = []
    monkeypatch.setattr(
        my_plugin_module.user,
        'set_cached_token',
        lambda *_args: stored_tokens.append((_args[1], _args[2])),
    )

    # Need to access the private method to test it
    # pylint: disable=protected-access
    my_plugin_module._attach_user_id_to_token()

    assert token['user_id'] == 'arte-user-id'
    assert stored_tokens == [('user@example.test', token)]
