"""
Scheme Luminance.

Determines the scheme luminance to discover if the theme is light or dark.
"""
import sublime
from plistlib import readPlistFromBytes
from .rgba import RGBA
import os
import re


def sublime_format_path(pth):
    """Format the path for sublime."""

    m = re.match(r"^([A-Za-z]{1}):(?:/|\\)(.*)", pth)
    if sublime.platform() == "windows" and m is not None:
        pth = m.group(1) + "/" + m.group(2)
    return pth.replace("\\", "/")


def scheme_lums(scheme_file):
    """Get the scheme lumincance."""
    color_scheme = os.path.normpath(scheme_file)
    scheme_file = os.path.basename(color_scheme)
    plist_file = readPlistFromBytes(
        re.sub(
            br"^[\r\n\s]*<!--[\s\S]*?-->[\s\r\n]*|<!--[\s\S]*?-->", b'',
            sublime.load_binary_resource(sublime_format_path(color_scheme))
        )
    )

    color_settings = plist_file["settings"][0]["settings"]
    rgba = RGBA(color_settings.get("background", '#FFFFFF'))
    return rgba.luminance()
