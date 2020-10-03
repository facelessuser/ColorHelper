"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
from textwrap import dedent
import platform
import mdpopups
import base64
import importlib

RE_COLOR_START = r"(?i)(?:\b(?:color|hsla?|gray|lch|lab|hwb|rgba?)\(|\b(?<!\#)[\w]{3,}(?!\()\b|\#)"

COLOR = {"color": True, "fit": False}
HEX = {"hex": True}
HEX_NA = {"hex": True, "alpha": False}
DEFAULT = {"fit": False}
FULL_PREC = {"fit": False, "precision": -1}
COLOR_FULL_PREC = {"color": True, "fit": False, "precision": -1}
SRGB_SPACES = ("srgb", "hsl", "hwb")

FRONTMATTER = mdpopups.format_frontmatter(
    {
        "allow_code_wrap": False,
        "markdown_extensions": [
            "markdown.extensions.admonition",
            "markdown.extensions.attr_list",
            "markdown.extensions.def_list",
            "pymdownx.betterem",
            "pymdownx.magiclink",
            "pymdownx.extrarawhtml"
        ]
    }
)

LINE_HEIGHT_WORKAROUND = platform.system() == "Windows"

ADD_CSS = dedent(
    '''
    div.color-helper { margin: 0; padding: 0.5rem; }
    .color-helper .small { font-size: 0.8rem; }
    .color-helper .alpha { text-decoration: underline; }
    '''
)

WRAPPER_CLASS = "color-helper content"

DEF_OUTPUT = [
    {"space": "srgb", "format": {"hex": True}},
    {"space": "srgb", "format": {"comma": True, "precision": 3}},
    {"space": "hsl", "format": {"comma": True, "precision": 3}},
    {"space": "hwb", "format": {"comma": False, "precision": 3}},
    {"space": "lch", "format": {"comma": False, "precision": 3}},
    {"space": "lab", "format": {"comma": False, "precision": 3}},
    {"space": "xyz", "format": {}}
]


def import_color(module_path):
    """Import color module."""

    module, color_class = module_path.rsplit('.', 1)
    color_class = getattr(importlib.import_module(module), color_class)
    return color_class


def encode_color(color):
    """Encode color into base64 for URL links."""

    return base64.b64encode(color.encode('utf-8')).decode('utf-8')


def decode_color(color):
    """Decode color from base64 for URL links."""

    return base64.b64decode(color.encode('utf-8')).decode('utf-8')


def html_encode(txt):
    """HTML encode."""

    txt = txt.replace('&', '&amp;')
    txt = txt.replace('<', '&lt;')
    txt = txt.replace('>', '&gt;')
    return txt


def log(*args):
    """Log."""

    text = ['\nColorHelper: ']
    for arg in args:
        text.append(str(arg))
    text.append('\n')
    print(''.join(text))


def debug(*args):
    """Log if debug enabled."""

    if sublime.load_settings("color_helper.sublime-settings").get('debug', False):
        log(*args)


def get_line_height(view):
    """Get the line height."""

    height = view.line_height()
    settings = sublime.load_settings("color_helper.sublime-settings")

    return int((height / 2.0) if LINE_HEIGHT_WORKAROUND and settings.get('line_height_workaround', False) else height)


def color_picker_available():
    """Check if color picker is available."""

    s = sublime.load_settings('color_helper_share.sublime-settings')
    s.set('color_pick_return', None)
    sublime.run_command('color_pick_api_is_available', {'settings': 'color_helper_share.sublime-settings'})
    return s.get('color_pick_return', None)


def get_rules(view):
    """Get auto-popup scope rule."""

    rules = view.settings().get("color_helper.scan")

    return rules if rules is not None and rules.get("enabled", False) else None


def get_scope(view, rules, skip_sel_check=False):
    """Get auto-popup scope rule."""

    scopes = None
    if rules is not None:
        scopes = ','.join(rules.get('scan_scopes', []))
        sels = view.sel()
        if not skip_sel_check:
            if len(sels) == 0 or not scopes or view.score_selector(sels[0].begin(), scopes) == 0:
                scopes = None
    return scopes


def get_favs():
    """Get favorites object."""

    bookmark_colors = sublime.load_settings('color_helper.palettes').get("favorites", [])
    return {"name": "Favorites", "colors": bookmark_colors}


def save_palettes(palettes, favs=False):
    """Save palettes."""

    s = sublime.load_settings('color_helper.palettes')
    if favs:
        s.set('favorites', palettes)
    else:
        s.set('palettes', palettes)
    sublime.save_settings('color_helper.palettes')


def save_project_palettes(window, palettes):
    """Save project palettes."""

    data = window.project_data()
    if data is None:
        data = {'color_helper_palettes': palettes}
    else:
        data['color_helper_palettes'] = palettes
    window.set_project_data(data)


def get_palettes():
    """Get palettes."""

    return sublime.load_settings('color_helper.palettes').get("palettes", [])


def get_project_palettes(window):
    """Get project palettes."""
    data = window.project_data()
    if data is None:
        data = {}
    return data.get('color_helper_palettes', [])


def get_project_folders(window):
    """Get project folder."""
    data = window.project_data()
    if data is None:
        data = {'folders': [{'path': f} for f in window.folders()]}
    return data.get('folders', [])


def merge_rules(a, b):
    """Merge two rules."""
    c = a.copy()
    c.update(b)
    return c


def get_settings_rules():
    """Read rules from settings and allow overrides."""

    s = sublime.load_settings('color_helper.sublime-settings')
    rules = s.get("color_rules", [])
    user_rules = s.get("user_color_rules", [])
    names = {rule["name"]: i for i, rule in enumerate(rules) if "name" in rule}
    for urule in user_rules:
        name = urule.get("name")
        if name is not None and name in names:
            index = names[name]
            rules[index] = merge_rules(rules[index], urule)
        else:
            rules.append(urule)
    return rules


def get_settings_colors():
    """Read color classes from settings and allow overrides."""

    s = sublime.load_settings('color_helper.sublime-settings')
    classes = s.get("color_classes", {})
    user_classes = s.get("user_color_classes", {})
    for k, v in user_classes.items():
        if k not in classes:
            classes[k] = v
        else:
            classes[k] = merge_rules(classes[k], v)
    return classes
