"""ColorHelper utilities."""
import sublime
import re
import decimal
from ColorHelper.lib import csscolors
from ColorHelper.lib.rgba import RGBA, round_int, clamp

FLOAT_TRIM_RE = re.compile(r'^(?P<keep>\d+)(?P<trash>\.0+|(?P<keep2>\.\d*[1-9])0+)$')

COLOR_PARTS = {
    "percent": r"[+\-]?(?:(?:\d*\.\d+)|\d+)%",
    "float": r"[+\-]?(?:(?:\d*\.\d+)|\d+)"
}

COMPLETE = r'''
    (?P<hex>\#(?P<hex_content>[\dA-Fa-f]{6}))\b |
    (?P<hex_compressed>\#(?P<hex_compressed_content>[\dA-Fa-f]{3}))\b |
    (?P<hexa>\#(?P<hexa_content>[\dA-Fa-f]{8}))\b |
    (?P<hexa_compressed>\#(?P<hexa_compressed_content>[\dA-Fa-f]{4}))\b |
    \b(?P<rgb>rgb\(\s*(?P<rgb_content>(?:%(float)s\s*,\s*){2}%(float)s | (?:%(percent)s\s*,\s*){2}%(percent)s)\s*\)) |
    \b(?P<rgba>rgba\(\s*(?P<rgba_content>
        (?:%(float)s\s*,\s*){3}(?:%(percent)s|%(float)s) | (?:%(percent)s\s*,\s*){3}(?:%(percent)s|%(float)s)
    )\s*\)) |
    \b(?P<hsl>hsl\(\s*(?P<hsl_content>%(float)s\s*,\s*%(percent)s\s*,\s*%(percent)s)\s*\)) |
    \b(?P<hsla>hsla\(\s*(?P<hsla_content>%(float)s\s*,\s*(?:%(percent)s\s*,\s*){2}(?:%(percent)s|%(float)s))\s*\)) |
    \b(?P<hwb>hwb\(\s*(?P<hwb_content>%(float)s\s*,\s*%(percent)s\s*,\s*%(percent)s)\s*\)) |
    \b(?P<hwba>hwb\(\s*(?P<hwba_content>%(float)s\s*,\s*(?:%(percent)s\s*,\s*){2}(?:%(percent)s|%(float)s))\s*\)) |
    \b(?P<gray>gray\(\s*(?P<gray_content>%(float)s|%(percent)s)\s*\)) |
    \b(?P<graya>gray\(\s*(?P<graya_content>(?:%(float)s|%(percent)s)\s*,\s*(?:%(percent)s|%(float)s))\s*\))
''' % COLOR_PARTS

INCOMPLETE = r'''
    (?P<hash>\#) |
    \b(?P<rgb_open>rgb\() |
    \b(?P<rgba_open>rgba\() |
    \b(?P<hsl_open>hsl\() |
    \b(?P<hsla_open>hsla\() |
    \b(?P<hwb_open>hwb\() |
    \b(?P<gray_open>hwb\()
    '''

COLOR_NAMES = r'\b(?P<webcolors>%s)\b(?!\()' % '|'.join([name for name in csscolors.name2hex_map.keys()])

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

HEX_IS_GRAY_RE = re.compile(r'(?i)^#([0-9a-f]{2})\1\1')
HEX_COMPRESS_RE = re.compile(r'(?i)^#([0-9a-f])\1([0-9a-f])\2([0-9a-f])\3(?:([0-9a-f])\4)?$')

COLOR_RE = re.compile(r'(?x)(?i)(?!<[@#$.\-_])(?:%s|%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES))
COLOR_ALL_RE = re.compile(r'(?x)(?i)(?!<[@#$.\-_])(?:%s|%s|%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES, INCOMPLETE))
INDEX_ALL_RE = re.compile((r'(?x)(?i)(?!<[@#$.\-_])(?:%s|%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES)).encode('utf-8'))

ADD_CSS = '''
.color-helper.content { margin: 0; padding: 0.5em; }
.color-helper.small { font-size: 0.8em; }
.color-helper.alpha { text-decoration: underline; }
'''

CSS3 = ("webcolors", "hex", "hex_compressed", "rgb", "rgba", "hsl", "hsla")
CSS4 = CSS3 + ("gray", "graya", "hwb", "hwba", "hexa", "hexa_compressed")
ALL = CSS4


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


def color_picker_available():
    """Check if color picker is available."""

    s = sublime.load_settings('color_helper_share.sublime-settings')
    s.set('color_pick_return', None)
    sublime.run_command('color_pick_api_is_available', {'settings': 'color_helper_share.sublime-settings'})
    return s.get('color_pick_return', None)


def fmt_float(f, p=0):
    """Set float pring precision and trim precision zeros."""

    string = str(
        decimal.Decimal(f).quantize(decimal.Decimal('0.' + ('0' * p) if p > 0 else '0'), decimal.ROUND_HALF_UP)
    )

    m = FLOAT_TRIM_RE.match(string)
    if m:
        string = m.group('keep')
        if m.group('keep2'):
            string += m.group('keep2')
    return string


def get_rules(view):
    """Get auto-popup scope rule."""

    rules = view.settings().get("color_helper.scan", {})

    return rules if rules.get("enabled", False) else None


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


def get_scope_completion(view, rules, skip_sel_check=False):
    """Get additional auto-popup scope rules for incomplete colors only."""

    scopes = None
    if rules is not None:
        scopes = ','.join(rules.get('scan_completion_scopes', []))
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


def is_gray(color):
    """Check if color is gray (all channels the same)."""

    m = HEX_IS_GRAY_RE.match(color)
    return m is not None


def compress_hex(color):
    """Compress hex."""

    m = HEX_COMPRESS_RE.match(color)
    if m:
        color = '#' + m.group(1) + m.group(2) + m.group(3)
        if m.group(4):
            color += m.group(4)
    return color


def alpha_dec_normalize(dec):
    """Normailze a deciaml alpha value."""

    temp = float(dec)
    if temp < 0.0 or temp > 1.0:
        dec = fmt_float(clamp(float(temp), 0.0, 1.0), 3)
    alpha_dec = dec
    alpha = "%02X" % round_int(float(alpha_dec) * 255.0)
    return alpha, alpha_dec


def alpha_percent_normalize(perc):
    """Normailze a percent alpha value."""

    alpha_float = clamp(float(perc.strip('%')), 0.0, 100.0) / 100.0
    alpha_dec = fmt_float(alpha_float, 3)
    alpha = "%02X" % round_int(alpha_float * 255.0)
    return alpha, alpha_dec


def translate_color(m, use_hex_argb=False, decode=False):
    """Translate the match object to a color w/ alpha."""

    color = None
    alpha = None
    alpha_dec = None
    if m.group('hex_compressed'):
        if decode:
            content = m.group('hex_compressed_content').decode('utf-8')
        else:
            content = m.group('hex_compressed_content')
        color = "#%02x%02x%02x" % (
            int(content[0:1] * 2, 16), int(content[1:2] * 2, 16), int(content[2:3] * 2, 16)
        )
    elif m.group('hexa_compressed') and use_hex_argb:
        if decode:
            content = m.group('hexa_compressed_content').decode('utf-8')
        else:
            content = m.group('hexa_compressed_content')
        color = "#%02x%02x%02x" % (
            int(content[1:2] * 2, 16), int(content[2:3] * 2, 16), int(content[3:] * 2, 16)
        )
        alpha = content[0:1]
        alpha_dec = fmt_float(float(int(alpha, 16)) / 255.0, 3)
    elif m.group('hexa_compressed'):
        if decode:
            content = m.group('hexa_compressed_content').decode('utf-8')
        else:
            content = m.group('hexa_compressed_content')
        color = "#%02x%02x%02x" % (
            int(content[0:1] * 2, 16), int(content[1:2] * 2, 16), int(content[2:3] * 2, 16)
        )
        alpha = content[3:]
        alpha_dec = fmt_float(float(int(alpha, 16)) / 255.0, 3)
    elif m.group('hex'):
        if decode:
            content = m.group('hex_content').decode('utf-8')
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
    elif m.group('hexa') and use_hex_argb:
        if decode:
            content = m.group('hexa_content').decode('utf-8')
        else:
            content = m.group('hexa_content')
        if len(content) == 8:
            color = "#%02x%02x%02x" % (
                int(content[2:4], 16), int(content[4:6], 16), int(content[6:], 16)
            )
            alpha = content[0:2]
            alpha_dec = fmt_float(float(int(alpha, 16)) / 255.0, 3)
        else:
            color = "#%02x%02x%02x" % (
                int(content[1:2] * 2, 16), int(content[2:3] * 2, 16), int(content[3:] * 2, 16)
            )
            alpha = content[0:1]
            alpha_dec = fmt_float(float(int(alpha, 16)) / 255.0, 3)
    elif m.group('hexa'):
        if decode:
            content = m.group('hexa_content').decode('utf-8')
        else:
            content = m.group('hexa_content')
        if len(content) == 8:
            color = "#%02x%02x%02x" % (
                int(content[0:2], 16), int(content[2:4], 16), int(content[4:6], 16)
            )
            alpha = content[6:]
            alpha_dec = fmt_float(float(int(alpha, 16)) / 255.0, 3)
        else:
            color = "#%02x%02x%02x" % (
                int(content[0:1] * 2, 16), int(content[1:2] * 2, 16), int(content[2:3] * 2, 16)
            )
            alpha = content[3:]
            alpha_dec = fmt_float(float(int(alpha, 16)) / 255.0, 3)
    elif m.group('rgb'):
        if decode:
            content = [x.strip() for x in m.group('rgb_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('rgb_content').split(',')]
        if content[0].endswith('%'):
            r = round_int(clamp(float(content[0].strip('%')), 0.0, 255.0) * (255.0 / 100.0))
            g = round_int(clamp(float(content[1].strip('%')), 0.0, 255.0) * (255.0 / 100.0))
            b = round_int(clamp(float(content[2].strip('%')), 0.0, 255.0) * (255.0 / 100.0))
            color = "#%02x%02x%02x" % (r, g, b)
        else:
            color = "#%02x%02x%02x" % (
                clamp(round_int(float(content[0])), 0, 255),
                clamp(round_int(float(content[1])), 0, 255),
                clamp(round_int(float(content[2])), 0, 255)
            )
    elif m.group('rgba'):
        if decode:
            content = [x.strip() for x in m.group('rgba_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('rgba_content').split(',')]
        if content[0].endswith('%'):
            r = round_int(clamp(float(content[0].strip('%')), 0.0, 255.0) * (255.0 / 100.0))
            g = round_int(clamp(float(content[1].strip('%')), 0.0, 255.0) * (255.0 / 100.0))
            b = round_int(clamp(float(content[2].strip('%')), 0.0, 255.0) * (255.0 / 100.0))
            color = "#%02x%02x%02x" % (r, g, b)
        else:
            color = "#%02x%02x%02x" % (
                clamp(round_int(float(content[0])), 0, 255),
                clamp(round_int(float(content[1])), 0, 255),
                clamp(round_int(float(content[2])), 0, 255)
            )
        if content[3].endswith('%'):
            alpha, alpha_dec = alpha_percent_normalize(content[3])
        else:
            alpha, alpha_dec = alpha_dec_normalize(content[3])
    elif m.group('gray'):
        if decode:
            content = m.group('gray_content').decode('utf-8')
        else:
            content = m.group('gray_content')
        if content.endswith('%'):
            g = round_int(clamp(float(content.strip('%')), 0.0, 255.0) * (255.0 / 100.0))
        else:
            g = clamp(round_int(float(content)), 0, 255)
        color = "#%02x%02x%02x" % (g, g, g)
    elif m.group('graya'):
        if decode:
            content = [x.strip() for x in m.group('graya_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('graya_content').split(',')]
        if content[0].endswith('%'):
            g = round_int(clamp(float(content[0].strip('%')), 0.0, 255.0) * (255.0 / 100.0))
        else:
            g = clamp(round_int(float(content[0])), 0, 255)
        color = "#%02x%02x%02x" % (g, g, g)
        if content[1].endswith('%'):
            alpha, alpha_dec = alpha_percent_normalize(content[1])
        else:
            alpha, alpha_dec = alpha_dec_normalize(content[1])
    elif m.group('hsl'):
        if decode:
            content = [x.strip() for x in m.group('hsl_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('hsl_content').split(',')]
        rgba = RGBA()
        hue = float(content[0])
        if hue < 0.0 or hue > 360.0:
            hue = hue % 360.0
        h = hue / 360.0
        s = clamp(float(content[1].strip('%')), 0.0, 100.0) / 100.0
        l = clamp(float(content[2].strip('%')), 0.0, 100.0) / 100.0
        rgba.fromhls(h, l, s)
        color = rgba.get_rgb()
    elif m.group('hsla'):
        if decode:
            content = [x.strip() for x in m.group('hsla_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('hsla_content').split(',')]
        rgba = RGBA()
        hue = float(content[0])
        if hue < 0.0 or hue > 360.0:
            hue = hue % 360.0
        h = hue / 360.0
        s = clamp(float(content[1].strip('%')), 0.0, 100.0) / 100.0
        l = clamp(float(content[2].strip('%')), 0.0, 100.0) / 100.0
        rgba.fromhls(h, l, s)
        color = rgba.get_rgb()
        if content[3].endswith('%'):
            alpha, alpha_dec = alpha_percent_normalize(content[3])
        else:
            alpha, alpha_dec = alpha_dec_normalize(content[3])
    elif m.group('hwb'):
        if decode:
            content = [x.strip() for x in m.group('hwb_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('hwb_content').split(',')]
        rgba = RGBA()
        hue = float(content[0])
        if hue < 0.0 or hue > 360.0:
            hue = hue % 360.0
        h = hue / 360.0
        w = clamp(float(content[1].strip('%')), 0.0, 100.0) / 100.0
        b = clamp(float(content[2].strip('%')), 0.0, 100.0) / 100.0
        rgba.fromhwb(h, w, b)
        color = rgba.get_rgb()
    elif m.group('hwba'):
        if decode:
            content = [x.strip() for x in m.group('hwba_content').decode('utf-8').split(',')]
        else:
            content = [x.strip() for x in m.group('hwba_content').split(',')]
        rgba = RGBA()
        hue = float(content[0])
        if hue < 0.0 or hue > 360.0:
            hue = hue % 360.0
        h = hue / 360.0
        w = clamp(float(content[1].strip('%')), 0.0, 100.0) / 100.0
        b = clamp(float(content[2].strip('%')), 0.0, 100.0) / 100.0
        rgba.fromhwb(h, w, b)
        color = rgba.get_rgb()
        if content[3].endswith('%'):
            alpha, alpha_dec = alpha_percent_normalize(content[3])
        else:
            alpha, alpha_dec = alpha_dec_normalize(content[3])
    elif m.group('webcolors'):
        try:
            if decode:
                color = csscolors.name2hex(m.group('webcolors').decode('utf-8')).lower()
            else:
                color = csscolors.name2hex(m.group('webcolors')).lower()
        except:
            pass
    return color, alpha, alpha_dec
