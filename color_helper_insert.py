"""Calculate Insertion of color."""
import sublime
from ColorHelper.lib import csscolors
import ColorHelper.color_helper_util as util


class InsertionCalc(object):
    """Calculate and insert color."""

    def __init__(self, view, point, target_color, convert=None):
        """Initialize insertion object."""

        ch_settings = sublime.load_settings('color_helper.sublime-settings')
        self.convert = '' if convert is None else convert
        self.view = view
        self.convert_rgb = False
        self.convert_hsl = False
        self.alpha = None
        self.region = sublime.Region(point)
        self.format_override = False
        self.start = point - 50
        self.end = point + 50
        self.point = point
        visible = self.view.visible_region()
        if self.start < visible.begin():
            self.start = visible.begin()
        if self.end > visible.end():
            self.end = visible.end()
        self.use_web_colors = bool(ch_settings.get('use_webcolor_names', True))
        self.preferred_format = ch_settings.get('preferred_format', 'hex')
        self.preferred_alpha_format = ch_settings.get('preferred_alpha_format', 'rgba')
        self.force_alpha = False
        if self.convert:
            self.format_override = True
            if self.convert == "name":
                self.use_web_colors = True
                if len(target_color) > 7:
                    target_color = target_color[:-2]
            elif self.convert == 'hex':
                self.convert_rgb = False
                self.use_web_colors = False
            elif self.convert in ('rgb', 'rgba'):
                self.convert_rgb = True
                self.force_alpha = self.convert == 'rgba'
                self.use_web_colors = False
            elif self.convert in ('hsl', 'hsla'):
                self.convert_hsl = True
                self.force_alpha = self.convert == 'hsla'
                self.use_web_colors = False

        self.target_color = target_color
        try:
            self.web_color = csscolors.hex2name(target_color) if self.use_web_colors else None
        except:
            self.web_color = None

    def replacement(self, m):
        """See if match is a replacement of an existing color."""

        found = True
        if m.group('webcolors'):
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
            if self.preferred_format in ('rgb', 'hsl'):
                self.format_override = True
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
                else:
                    self.convert_hsl = True
        elif m.group('hex'):
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
            if self.preferred_format in ('rgb', 'hsl'):
                self.format_override = True
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
                else:
                    self.convert_hsl = True
        elif m.group('rgb'):
            if self.web_color:
                self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
            else:
                if self.preferred_format in ('hex', 'hsl') or self.convert:
                    self.format_override = True
                    self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
                    if self.preferred_format == 'hsl':
                        self.convert_hsl = True
                else:
                    self.region = sublime.Region(m.start('rgb_content') + self.start, m.end('rgb_content') + self.start)
                    self.convert_rgb = True
        elif m.group('rgba'):
            self.web_color = None
            if self.preferred_alpha_format == 'hsla' or self.convert:
                self.format_override = True
                self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
                self.convert_hsl = True
            else:
                self.region = sublime.Region(m.start('rgba_content') + self.start, m.end('rgba_content') + self.start)
                self.convert_rgb = True
            content = [x.strip() for x in m.group('rgba_content').split(',')]
            self.alpha = content[3]
        elif m.group('hsl'):
            if self.web_color:
                self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
            else:
                if self.preferred_format in ('hex', 'rgb') or self.convert:
                    self.format_override = True
                    self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
                    if self.preferred_format == 'rgb':
                        self.convert_rgb = True
                else:
                    self.region = sublime.Region(m.start('hsl_content') + self.start, m.end('hsl_content') + self.start)
                    self.convert_hsl = True
        elif m.group('hsla'):
            self.web_color = None
            if self.preferred_alpha_format == 'rgba' or self.convert:
                self.format_override = True
                self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
                self.convert_rgb = True
            else:
                self.region = sublime.Region(m.start('hsla_content') + self.start, m.end('hsla_content') + self.start)
                self.convert_hsl = True
            content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
            self.alpha = content[3]
        else:
            found = False
        return found

    def converting(self, m):
        """See if match is a convert replacement of an existing color."""
        found = True
        if m.group('webcolors'):
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
        elif m.group('hex'):
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
        elif m.group('rgb'):
            self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
        elif m.group('rgba'):
            self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
            content = [x.strip() for x in m.group('rgba_content').split(',')]
            self.alpha = content[3]
        elif m.group('hsl'):
            self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
        elif m.group('hsla'):
            self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
            content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
            self.alpha = content[3]
        else:
            found = False
        return found

    def convert_alpha(self):
        """Setup conversion alpha."""

        if self.force_alpha and self.alpha is None:
            self.alpha = '1'
        elif not self.force_alpha:
            self.alpha = None

    def completion(self, m):
        """See if match is completing an color."""

        found = True
        if m.group('hash'):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
            if self.preferred_format in ('rgb', 'hsl'):
                self.format_override = True
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
                else:
                    self.convert_hsl = True
        elif m.group('rgb_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.web_color:
                self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
            elif self.preferred_format in ('hex', 'hsl'):
                self.format_override = True
                self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
                if self.preferred_format == 'hsl':
                    self.convert_hsl = True
            else:
                self.convert_rgb = True
        elif m.group('rgba_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.preferred_alpha_format == 'hsla':
                self.format_override = True
                self.region = sublime.Region(m.start('rgba_open') + self.start, m.end('rgb_open') + self.start + offset)
                self.convert_hsl = True
            else:
                self.convert_rgb = True
            self.alpha = '1'
        elif m.group('hsl_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.web_color:
                self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
            elif self.preferred_format in ('hex', 'rgb'):
                self.format_override = True
                self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
            else:
                self.convert_hsl = True
        elif m.group('hsla_open'):
            self.offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.preferred_alpha_format == 'rgba':
                self.format_override = True
                self.region = sublime.Region(
                    m.start('hsla_open') + self.start, m.end('hsla_open') + self.start + offset
                )
                self.convert_rgb = True
            else:
                self.convert_hsl = True
            self.alpha = '1'
        else:
            found = False
        return found

    def calc(self):
        """Calculate how we are to insert the target color."""

        bfr = self.view.substr(sublime.Region(self.start, self.end))
        ref = self.point - self.start
        found = False

        for m in util.COLOR_ALL_RE.finditer(bfr):
            if self.convert:
                if ref >= m.start(0) and ref < m.end(0):
                    found = self.converting(m)
                elif ref < m.start(0):
                    break
            elif ref >= m.start(0) and ref < m.end(0):
                found = self.replacement(m)
            elif ref == m.end(0):
                found = self.completion(m)
            elif ref < m.start(0):
                break
            if found:
                break

        if self.convert:
            self.convert_alpha()

        return found
