"""Small helper to replace xbmcswift2.actions used by the addon.
Provide background(...) and update_view(...) helpers that return RunPlugin strings
for context-menu commands.
"""


def background(url):
    """Return a RunPlugin command string to execute url from context menu."""
    return f"RunPlugin({url})"


def update_view(url):
    """Return a RunPlugin command string used to update the view (same as RunPlugin)."""
    return f"RunPlugin({url})"
