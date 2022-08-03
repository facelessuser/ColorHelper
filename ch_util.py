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
from .lib.coloraide import Color as Base
from .lib.coloraide.css.parse import RE_COLOR_MATCH
from .lib.coloraide import __version_info__ as coloraide_version
import functools

SUPPORTED_SPACES = list(Base.CS_MAP.values())


class Color(Base):
    """Custom base."""


PALETTE_CONFIG = 'color_helper.palettes'
REQUIRED_COLOR_VERSION = (0, 1, 0, 'alpha', 19)
UPDATE_COLORS = RE_COLOR_MATCH
COLOR_FMT_1_0 = (0, 1, 0, 'alpha', 19)
COLOR_FMT_2_0 = (0, 3, 0, 'final')
PALETTE_FMT = (2, 0)

RE_COLOR_START = r"""(?xi)
(?:
    \b(?<![-#&$])(?:
        color\((?!\s*-)|(?:hsla?|(?:ok)?(?:lch|lab)|hwb|rgba?)\(
) |
\b(?<![-#&$])[\w]{3,}(?![(-])\b|(?<![&])\#)
"""

COLOR = {"color": True, "fit": False}
HEX = {"hex": True}
HEX_NA = {"hex": True, "alpha": False}
DEFAULT = {"fit": False}
COMMA = {"fit": False, "comma": True}
FULL_PREC = {"fit": False, "precision": -1}
COLOR_PIC_FULL_PREC = {"color": True, "fit": 'clip', "precision": 0}
COLOR_FULL_PREC = {"color": True, "fit": False, "precision": -1}
COLOR_SERIALIZE = {"color": True, "fit": False, "precision": -1}
SRGB_SPACES = ("srgb", "hsl", "hwb", "hsv")
CSS_SRGB_SPACES = ("srgb", "hsl", "hwb")
EXTENDED_SRGB_SPACES = ("srgb", "hsl", "hwb", "okhsl", "hsv", "okhsv", "hsluv")
CSS_L4_SPACES = (
    "srgb", "hsl", "hwb", "lch", "lab", "display-p3", "rec2020",
    "prophoto-rgb", "a98-rgb", "xyz-d65", "xyz-d50", "srgb-linear"
)
GAMUT_SPACES = ("srgb", "display-p3", "rec2020", "prophoto-rgb", "a98-rgb")

lang_map = {
    # `'name': (('mapping_alias',), ('tmLanguage_or_sublime-syntax file',))`
    'color-helper': (('color-helper',), ('ColorHelper/color-helper-colors',))
}

FRONTMATTER = mdpopups.format_frontmatter(
    {
        "allow_code_wrap": False,
        "language_map": lang_map,
        "markdown_extensions": [
            "markdown.extensions.admonition",
            "markdown.extensions.attr_list",
            "markdown.extensions.def_list",
            "markdown.extensions.md_in_html",
            "pymdownx.inlinehilite",
            "pymdownx.betterem",
            "pymdownx.magiclink"
        ]
    }
)

LINE_HEIGHT_WORKAROUND = platform.system() == "Windows"

ADD_CSS = dedent(
    '''
    html.light {
      --ch-button-color: color(var(--mdpopups-bg) blend(black 85%));
    }
    html.dark {
      --ch-button-color: color(var(--mdpopups-bg) blend(white 85%));
    }
    div.color-helper { margin: 0; padding: 0rem; }

    .color-helper .small { font-size: 0.8rem; }
    .color-helper a { text-decoration: none; }
    .color-helper .comment {
        font-size: 0.8rem;
        font-style: italic;
        color: color(var(--mdpopups-fg) a(50%));
    }

    .color-helper div.menu a {
        line-height: 0.8rem;
        font-size: 0.8rem;
        color: var(--mdpopups-fg);
    }
    .color-helper div.menu {
        padding: 0.5rem 0.5rem 0 0.5rem;
        margin: 0;
        background-color: var(--ch-button-color);
    }
    .color-helper div.menu a {
        padding: 0.25rem;
    }
    .color-helper div.panel {
        padding: 0.5rem;
        margin: 0;
    }

    .color-helper div.buttons {
        padding: 0 0.5rem;
        padding-top: 0;
    }

    .color-helper code.highlight {
        font-size: inherit;
    }

    .color-helper a.button {
        font-size: 0.8rem;
        line-height: 0.8rem;
        padding: 0.15rem 0.25rem;
        color:  var(--mdpopups-fg);
        background-color: var(--ch-button-color);
        border-radius: 0.25rem;
    }

    .color-helper a.button.selected {
        border: 1px solid color(var(--mdpopups-fg) a(75%));
    }

    .color-helper hr {
        border-color: var(--ch-button-color);
    }

    .color-helper .center {
        text-align: center;
    }

    .color-helper a.fav {
        font-size: 2rem;
        line-height: 2rem;
        padding: 0.15rem 0.25rem;
        color:  var(--mdpopups-fg);
    }

    .color-helper a.fav.unselected {
        color:  color(var(--mdpopups-fg) a(25%));
    }

    .color-helper div.menu a.close {
        background-color: var(--mdpopups-fg);
        padding: 0.1rem 0.25rem;
        color: var(--mdpopups-bg);
        border-radius: 0.25rem;
    }
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
    {"space": "xyz-d65", "format": {}}
]


@functools.lru_cache()
def get_base_color():
    """Get base color."""

    Color.deregister('space:*')
    Color.register(SUPPORTED_SPACES)
    settings = sublime.load_settings("color_helper.sublime-settings")
    spaces = settings.get('add_to_default_spaces', [])
    for space in spaces:
        try:
            Color.register(import_color(space)())
        except Exception:
            log('Could not register: {}'.format(space))
    return Color


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


def update_colors_2_0(colors):
    """Update colors for version 2.0."""

    base = get_base_color()
    new_colors = []
    for c in colors:
        try:
            m = UPDATE_COLORS.match(c)
            if m and m.group(1) in ('xyz', '--xyz-d65'):
                space = m.group(1)
                values = m.group(2).split('/')
                channels = [float(x) for x in values[0].split(' ')]

                if len(values) > 1:
                    alpha = float(values[1])
                else:
                    alpha = 1

                if space == 'xyz':
                    space = 'xyz-d50'
                elif space == '--xyz-d65':
                    space = 'xyz-d65'

                new_colors.append(base(space.lstrip('-'), channels, alpha).to_string(**COLOR_SERIALIZE))
            else:
                new_colors.append(c)
        except Exception:
            pass
    return new_colors


def update_colors_1_0(colors):
    """Update colors for version 1.0."""

    base = get_base_color()
    new_colors = []
    for c in colors:
        try:
            m = UPDATE_COLORS.match(c)
            if m:
                space = m.group(1)
                values = m.group(2).split('/')
                channels = [float(x.rstrip('%')) for x in values[0].split(' ')]
                if space in ('--hsl', '--hsv'):
                    channels[1] = channels[1] / 100
                    channels[2] = channels[2] / 100
                if len(values) > 1:
                    alpha = float(values[1])
                else:
                    alpha = 1
                new_colors.append(base(space.lstrip('-'), channels, alpha).to_string(**COLOR_SERIALIZE))
            else:
                new_colors.append(base(c).to_string(**COLOR_SERIALIZE))
        except Exception:
            pass
    return new_colors


def _get_palettes(window=None):
    """Get palettes."""

    if window is None:
        palettes = sublime.load_settings(PALETTE_CONFIG)
        fmt = tuple([int(x) for x in palettes.get('__format__', '0.0').split('.')])
        if fmt != PALETTE_FMT and coloraide_version >= COLOR_FMT_1_0:
            if fmt == (0, 0):
                favs = update_colors_1_0(palettes.get('favorites', []))
                palettes.set('favorites', favs)
                all_pallets = palettes.get('palettes', [])
                for p in all_pallets:
                    p['colors'] = update_colors_1_0(p['colors'])
                palettes.set('palettes', all_pallets)
                palettes.set('__format__', '1.0')
                sublime.save_settings(PALETTE_CONFIG)
                fmt = (1, 0)
        if fmt != PALETTE_FMT and coloraide_version >= COLOR_FMT_2_0:
            if fmt == (1, 0):
                favs = update_colors_2_0(palettes.get('favorites', []))
                palettes.set('favorites', favs)
                all_pallets = palettes.get('palettes', [])
                for p in all_pallets:
                    p['colors'] = update_colors_1_0(p['colors'])
                palettes.set('palettes', all_pallets)
                palettes.set('__format__', '2.0')
                sublime.save_settings(PALETTE_CONFIG)
    else:
        data = window.project_data()
        if data is None:
            data = {
                'color_helper_palettes_format': '.'.join(str(x) for x in PALETTE_FMT),
                'color_helper_palettes': []
            }
        color_palettes = data.get('color_helper_palettes', [])
        if color_palettes:
            fmt = tuple([int(x) for x in data.get('color_helper_palettes_format', '0.0').split('.')])
            if fmt != PALETTE_FMT and coloraide_version >= COLOR_FMT_1_0:
                if fmt == (0, 0):
                    for p in color_palettes:
                        p['colors'] = update_colors_1_0(p['colors'])
                    data['color_helper_palettes'] = color_palettes
                    fmt = (1, 0)
                    data['color_helper_palettes_format'] = '.'.join(str(x) for x in fmt)
                    window.set_project_data(data)
                if fmt != PALETTE_FMT and coloraide_version >= COLOR_FMT_2_0:
                    if fmt == (1, 0):
                        for p in color_palettes:
                            p['colors'] = update_colors_2_0(p['colors'])
                        data['color_helper_palettes'] = color_palettes
                        data['color_helper_palettes_format'] = '.'.join(str(x) for x in PALETTE_FMT)
                        window.set_project_data(data)

        palettes = data
    return palettes


def get_favs():
    """Get favorites object."""

    bookmark_colors = _get_palettes().get("favorites", [])
    return {"name": "Favorites", "colors": bookmark_colors}


def save_palettes(palettes, favs=False):
    """Save palettes."""

    s = _get_palettes()
    if favs:
        s.set('favorites', palettes)
    else:
        s.set('palettes', palettes)
    sublime.save_settings(PALETTE_CONFIG)


def save_project_palettes(window, palettes):
    """Save project palettes."""

    data = _get_palettes(window)
    data['color_helper_palettes'] = palettes
    window.set_project_data(data)


def get_palettes():
    """Get palettes."""

    return _get_palettes().get("palettes", [])


def get_project_palettes(window):
    """Get project palettes."""

    return _get_palettes(window).get('color_helper_palettes', [])


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
