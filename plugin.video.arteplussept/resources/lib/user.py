"""
Manage Arte user content and state e.g. favorites and last vieweds.
Manage settings and user interactions to create a token.
Manage token in cache. Avoid storing password in settings, only token.
"""
import time
# pylint: disable=import-error
from xbmcswift2 import xbmc
from xbmcswift2 import xbmcgui

from resources.lib import api

# key to manage token in plugin storage
_STORAGE_KEY = 'token'
# Time to live of 30d
_TTL = 30*24*60


def login(plugin, settings):
    """
    Unified login entry point.
    User chooses between:
    - Password login
    - Smart-TV Device login
    """
    erase_password_in_old_config(plugin)

    choice = xbmcgui.Dialog().select(
        plugin.addon.getLocalizedString(30057),
        [
            "Login with Smart‑TV device code",
            "Login with email & password"
        ]
    )
    if choice == 0:
        return login_with_device_flow(plugin, settings)
    if choice == 1:
        return login_with_password(plugin, settings)
    return False


# ---------------------------------------------------------------------------
# PASSWORD LOGIN (existing logic, untouched)
# ---------------------------------------------------------------------------

def login_with_password(plugin, settings):
    """
    Get user password from UI, create a token with Arte API, persist it in storage
    and update settings state to show user is logged in.
    """
    # ensure user to log in is identified
    usr = settings.username
    if not usr:
        msg = f"{plugin.addon.getLocalizedString(30020)} : {plugin.addon.getLocalizedString(30021)}"
        plugin.notify(msg=msg, image='error')
        return False

    # ensure no user is not logged in
    loggedin_usr = settings.user_email
    tkn_data = get_cached_token(plugin, usr, True)
    if len(loggedin_usr) > 0 and tkn_data:
        xbmc.log(
            f"\"{loggedin_usr}\" already authenticated : {tkn_data['access_token']}",
            level=xbmc.LOGINFO)
        # notify user that current token might be replaced
        accept_to_replace = xbmcgui.Dialog().yesno(
            plugin.addon.getLocalizedString(30015),
            plugin.addon.getLocalizedString(30016).format(new_user=usr, old_user=loggedin_usr),
            autoclose=10000
        )
        # user didn't accept replacement, so leave
        if not accept_to_replace:
            xbmc.log('Authentication aborted by user - keep initial token', level=xbmc.LOGWARNING)
            return False

    # get password
    pwd = get_user_password(plugin)
    if not pwd:
        xbmc.log('Authentication aborted by user - no password entered', level=xbmc.LOGWARNING)
        msg = f"{plugin.addon.getLocalizedString(30020)} : {plugin.addon.getLocalizedString(30022)}"
        plugin.notify(msg=msg, image='error')
        return False

    # get token for user and password
    tokens = api.authenticate_in_arte(plugin, usr, pwd)
    if tokens is None:
        xbmc.log('Authentication failed in arte', level=xbmc.LOGERROR)
        msg = f"{plugin.addon.getLocalizedString(30020)}"
        plugin.notify(msg=msg, image='error')
        return False

    # store token
    set_cached_token(plugin, usr, tokens)
    update_settings_state(plugin, usr)
    msg = plugin.addon.getLocalizedString(30017).format(user=usr)
    plugin.notify(msg=msg, image='info')
    return True


def get_user_password(plugin):
    """
    Display a keyboard to get user password.
    Return None. If user didn't enter a password or close the UI.
    """
    user_password = ''
    keyboard = xbmc.Keyboard(user_password, plugin.addon.getLocalizedString(30019), True)
    keyboard.doModal()
    if keyboard.isConfirmed() is False:
        return None
    user_password = keyboard.getText()
    if len(user_password) == 0:
        return None
    return user_password


# ---------------------------------------------------------------------------
# SMART-TV DEVICE FLOW LOGIN (new)
# ---------------------------------------------------------------------------

def login_with_device_flow(plugin, settings):
    """
    Smart-TV Device Authorization Flow:
    1. Request device_code + user_code
    2. Show QR code + user_code to user and steps to authenticate on another device
    3. Poll token endpoint until success
    4. Store token
    """
    xbmc.log("Starting ARTE Smart-TV device login", level=xbmc.LOGINFO)

    # Step 1 - request device_code
    device_info = api.device_authorization_request()
    if not device_info:
        plugin.notify(msg="Device login failed: cannot contact ARTE", image='error')
        return False

    device_code = device_info["device_code"]
    user_code = device_info["user_code"]
    verification_uri = device_info["verification_uri"]
    # verification_uri_complete = device_info["verification_uri_complete"]
    interval = device_info.get("interval", 5)

    # Step 2 - show QR code + user_code
    show_device_login_dialog(user_code, verification_uri)

    # Step 3 - poll token endpoint
    tokens = poll_device_token(device_code, interval)
    if tokens is None:
        plugin.notify(msg="Device login failed", image='error')
        return False

    # Step 4 - store token
    usr = settings.username
    set_cached_token(plugin, usr, tokens)
    update_settings_state(plugin, usr)
    # TODO set the right notification
    msg = plugin.addon.getLocalizedString(30017).format(user=usr)
    plugin.notify(msg=msg, image='info')
    return True


def show_device_login_dialog(user_code, verification_uri):
    """
    Display QR code + user_code in a Kodi dialog.
    """
    xbmcgui.Dialog().ok(
        "ARTE Smart‑TV Login",
        f"Enter the code {user_code} at {verification_uri} from your mobile device or computer."
    )

    # qr = qrcode.make(verification_uri_complete)
    # qr_path = xbmcmixin.temp_fn("arte_tvlogin_qr.png")
    # qr.save(stream=qr_path, format="PNG")
    # # buffer = BytesIO()
    # # with open(qr_path, "wb") as qr_file:
    # #     qr_file.write(buffer.getvalue())
    # show_qr_window(qr_path, user_code, verification_uri)


# def show_qr_window(qr_path, user_code, verification_uri):
#     """
#     Display a window with QR code and information to authenticate.
#     """
#     win = xbmcgui.WindowDialog()

#     lbl = xbmcgui.ControlLabel(
#         200, 720, 600, 40,
#         f"Enter the code [b]{user_code}[/b] at [{verification_uri}] on your mobile.\n\
#         Or scan the QR code.",
#         textColor="white", alignment=2)
#     img = xbmcgui.ControlImage(200, 100, 600, 600, qr_path)

#     win.addControl(img)
#     win.addControl(lbl)

#     win.doModal()
#     del win


def poll_device_token(device_code, interval):
    """
    Poll ARTE token endpoint until:
    - authorization_pending
    - slow_down
    - success (returns tokens)
    - error (returns None)
    """
    while True:
        data = api.device_token_request(device_code)

        if "access_token" in data:
            return data

        error = data.get("error")

        if error == "authorization_pending":
            time.sleep(interval)
            continue

        if error == "slow_down":
            interval += 5
            time.sleep(interval)
            continue

        xbmc.log(f"Device login error: {error}", level=xbmc.LOGERROR)
        return None


# ---------------------------------------------------------------------------
# EXISTING UTILITIES (unchanged)
# ---------------------------------------------------------------------------


def logout(plugin, settings):
    """Delete user token and reset settings state"""
    erase_password_in_old_config(plugin)

    usr = settings.username
    cached_token = get_cached_token(plugin, usr, silent=True)

    # Revoke refresh token if available - clear token remotely
    if cached_token and "refresh_token" in cached_token:
        refresh_token = cached_token["refresh_token"]
        if api.revoke_token(refresh_token):
            xbmc.log("ARTE token successfully revoked", level=xbmc.LOGINFO)
        else:
            xbmc.log("Failed to revoke ARTE token", level=xbmc.LOGWARNING)
    # clear token locally
    set_cached_token(plugin, settings.username, '')
    clear_cached_tokens(plugin)
    update_settings_state(plugin, '')
    plugin.notify(msg=plugin.addon.getLocalizedString(30018), image='info')
    return True


def update_settings_state(plugin, email):
    """Update setting state to know who belong the token to"""
    message = plugin.addon.getLocalizedString(30017).format(user=email)
    if email is None or len(email) <= 0:
        message = plugin.addon.getLocalizedString(30018)
    return plugin.set_setting('user_email', email) and plugin.set_setting('login_acc', message)


def get_cached_token(plugin, token_idx, silent=False):
    """
    Return cached token for identified user or None.
    If no token is in cache and silent is not True, then it warns user
    about the need to authenticate.
    If user logged in and later changed the user email, it returns None.
    """
    cached_token = plugin.get_storage(_STORAGE_KEY, TTL=_TTL)
    if token_idx in cached_token and isinstance(cached_token[token_idx], dict):
        tokens = cached_token[token_idx]
    else:
        tokens = None
        if not silent:
            plugin.notify(msg=plugin.addon.getLocalizedString(30014), image='warning')
    return tokens


def set_cached_token(plugin, token_idx, tokens):
    """Set cached token"""
    cached_token = plugin.get_storage(_STORAGE_KEY)
    cached_token[token_idx] = tokens


def clear_cached_tokens(plugin):
    """Clear every tokens. Not just the one of the user in parameter."""
    cached_token = plugin.get_storage(_STORAGE_KEY)
    cached_token.clear()


def erase_password_in_old_config(plugin):
    """
    Clean old password, that could be stored in settings from old way
    to authenticate user.
    Deprecated since creation JUL2023, v1.3.0.
    """
    return plugin.set_setting('password', '')
