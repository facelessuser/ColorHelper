"""ColorHelper utilities."""
import sublime
import re
import os
from ColorHelper.lib import csscolors
from ColorHelper.lib.rgba import RGBA

FLOAT_TRIM_RE = re.compile(r'^(?P<keep>\d+)(?P<trash>\.0+|(?P<keep2>\.\d*[1-9])0+)$')

HEX_RE = re.compile(r'^(?P<hex>\#(?P<hex_content>(?:[\dA-Fa-f]{3}){1,2}))$')

COMPLETE = r'''(?x)
    (?P<hex>\#(?P<hex_content>(?:[\dA-Fa-f]{3}){1,2}))\b |
    \b(?P<rgb>rgb\(\s*(?P<rgb_content>(?:\d+\s*,\s*){2}\d+)\s*\)) |
    \b(?P<rgba>rgba\(\s*(?P<rgba_content>(?:\d+\s*,\s*){3}(?:(?:\d*\.\d+)|\d))\s*\)) |
    \b(?P<hsl>hsl\(\s*(?P<hsl_content>\d+\s*,\s*(?:(?:\d*\.\d+)|\d+)%\s*,\s*(?:(?:\d*\.\d+)|\d+)%)\s*\)) |
    \b(?P<hsla>hsla\(\s*(?P<hsla_content>\d+\s*,\s*(?:(?:(?:\d*\.\d+)|\d+)%\s*,\s*){2}(?:(?:\d*\.\d+)|\d))\s*\))'''

INCOMPLETE = r''' |
    (?P<hash>\#) |
    \b(?P<rgb_open>rgb\() |
    \b(?P<rgba_open>rgba\() |
    \b(?P<hsl_open>hsl\() |
    \b(?P<hsla_open>hsla\()'''

COLOR_NAMES = r'| (?i)\b(?P<webcolors>%s)\b' % '|'.join([name for name in csscolors.name2hex_map.keys()])

TAG_HTML_RE = re.compile(
    br'''(?x)(?i)
    (?:
        (?P<comments>(\r?\n?\s*)<!--[\s\S]*?-->(\s*)(?=\r?\n)|<!--[\s\S]*?-->)|
        (?P<style><style((?:\s+[\w\-:]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^>\s]+))?)*)\s*>(?P<css>.*?)<\/style[^>]*>) |
        (?P<open><[\w\:\.\-]+)
        (?P<attr>(?:\s+[\w\-:]+(?:\s*=\s*(?:"[^"]*"|'[^']*'))?)*)
        (?P<close>\s*(?:\/?)>)
    )
    ''',
    re.DOTALL
)

TAG_STYLE_ATTR_RE = re.compile(
    br'''(?x)
    (?P<attr>
        (?:
            \s+style
            (?:\s*=\s*(?P<content>"[^"]*"|'[^']*'))
        )
    )
    ''',
    re.DOTALL
)

COLOR_RE = re.compile(r'(?!<[@#$.\-_])(?:%s%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES))
COLOR_ALL_RE = re.compile(r'(?!<[@#$.\-_])(?:%s%s%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES, INCOMPLETE))
INDEX_ALL_RE = re.compile((r'(?!<[@#$.\-_])(?:%s%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES)).encode('utf-8'))

ADD_CSS = '''
.color-helper.small {
    font-size: 0.8em;
}
'''


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


def get_cache_dir():
    """Get the cache dir."""

    return os.path.join(sublime.packages_path(), "User", 'ColorHelper.cache')


def color_picker_available():
    """Check if color picker is available."""

    s = sublime.load_settings('color_helper_share.sublime-settings')
    s.set('color_pick_return', None)
    sublime.run_command('color_pick_api_is_available', {'settings': 'color_helper_share.sublime-settings'})
    return s.get('color_pick_return', None)


def fmt_float(f, p=0):
    """Set float pring precision and trim precision zeros."""

    string = ("%." + "%d" % p + "f") % f
    m = FLOAT_TRIM_RE.match(string)
    if m:
        string = m.group('keep')
        if m.group('keep2'):
            string += m.group('keep2')
    return string


def is_hex_color(color):
    """Check if color is a hex color."""

    return color is not None and HEX_RE.match(color) is not None


def get_scope(view, skip_sel_check=False):
    """Get auto-popup scope rule."""
    ch_settings = sublime.load_settings('color_helper.sublime-settings')
    scopes = ','.join(ch_settings.get('supported_syntax', []))
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


def translate_color(m, decode=False):
    """Translate the match object to a color w/ alpha."""

    color = None
    alpha = None
    if m.group('hex'):
        if decode:
            content = m.group('hex_content')
        else:
            content = m.group('hex_content')
        if len(content) == 6:
            color = "#%02x%02x%02x" % (
                int(content[0:2], 16), int(content[2:4], 16), int(content[4:6], 16)
            )
        else:
            color = "#%02x%02x%02x" % (
                int(content[0:1] * 2, 16), int(content[1:2] * 2, 16), int(content[2:3] * 2, 16)
            )
    elif m.group('rgb'):
        if decode:
            content = [x.strip() for x in m.group('rgb_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('rgb_content').split(',')]
        color = "#%02x%02x%02x" % (
            int(content[0]), int(content[1]), int(content[2])
        )
    elif m.group('rgba'):
        if decode:
            content = [x.strip() for x in m.group('rgba_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('rgba_content').split(',')]
        color = "#%02x%02x%02x" % (
            int(content[0]), int(content[1]), int(content[2])
        )
        alpha = content[3]
    elif m.group('hsl'):
        if decode:
            content = [x.strip() for x in m.group('hsl_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('hsl_content').split(',')]
        rgba = RGBA()
        h = float(content[0]) / 360.0
        s = float(content[1].strip('%')) / 100.0
        l = float(content[2].strip('%')) / 100.0
        rgba.fromhls(h, l, s)
        color = rgba.get_rgb()
    elif m.group('hsla'):
        if decode:
            content = [x.strip() for x in m.group('hsla_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('hsla_content').split(',')]
        rgba = RGBA()
        h = float(content[0]) / 360.0
        s = float(content[1].strip('%')) / 100.0
        l = float(content[2].strip('%')) / 100.0
        rgba.fromhls(h, l, s)
        color = rgba.get_rgb()
        alpha = content[3]
    elif m.group('webcolors'):
        try:
            if decode:
                color = csscolors.name2hex(m.group('webcolors').decode('utf-8')).lower()
            else:
                color = csscolors.name2hex(m.group('webcolors')).lower()
        except:
            pass
    return color, alpha
