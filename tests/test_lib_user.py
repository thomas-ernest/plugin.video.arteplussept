"""Tests for Arte user token utilities."""
from unittest.mock import Mock

# pylint: disable=import-error
import pytest


# pylint: disable=wrong-import-position, import-error, no-name-in-module
from resources.lib import user as user_module  # noqa: E402
from resources.lib.user import _is_future, _normalize_and_anchor_expiry_date  # noqa: E402
from resources.lib.user import poll_device_token  # noqa: E402


@pytest.mark.parametrize(
    "token, expected",
    [({"expires_in": "2028-08-02T18:22:44+00:00"}, True),
     ({"expires_in": "2020-08-02T18:22:44+00:00"}, False),
     ({"expires_in": None}, False),
     (None, False),
     ({"created": 1788264710, "expires_in": 864000}, True),
     ({"created": 17864710, "expires_in": 86400}, False),
     ({"created": 1788244710, "expires_in": 6400}, False)]
)
def test_is_normalized_token_future(token, expected):
    """An unexpired Arte token is reported as the boolean True."""
    result = _is_future(_normalize_and_anchor_expiry_date(token)['expires_in'] if token else None)

    assert result is expected
    assert isinstance(result, bool)


def test_poll_device_token_stops_after_authorization_expiry(monkeypatch):
    """Pending device authorization stops when its expiry deadline is reached."""
    token_request = Mock(return_value={"error": "authorization_pending"})
    monotonic = Mock(side_effect=[0, 0, 0, 11])
    sleep = Mock()
    monkeypatch.setattr(user_module.api, "device_token_request", token_request)
    monkeypatch.setattr(user_module.time, "monotonic", monotonic)
    monkeypatch.setattr(user_module.time, "sleep", sleep)

    result = poll_device_token("device-code", 5, 10)

    assert result is None
    token_request.assert_called_once_with("device-code")
    sleep.assert_called_once_with(5)
