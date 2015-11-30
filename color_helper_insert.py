"""Calculate Insertion of color."""
import sublime
from ColorHelper.lib import csscolors
import ColorHelper.color_helper_util as util


class InsertCalc(object):
    """Convert."""

    def __init__(self, view, point, target_color, convert, use_argb):
        """Initialize."""

        self.convert_rgb = False
        self.convert_hsl = False
        self.alpha = None
        self.use_argb = use_argb
        self.alpha_hex = None
        self.view = view
        self.start = point - 50
        self.end = point + 50
        self.point = point
        self.region = sublime.Region(point)
        self.format_override = True

        visible = self.view.visible_region()
        if self.start < visible.begin():
            self.start = visible.begin()
        if self.end > visible.end():
            self.end = visible.end()
        self.web_color = None
        self.color = target_color[:-2] if len(target_color) > 7 else target_color

        if convert == "name":
            try:
                if len(target_color) > 7:
                    target_color = target_color[:-2]
                self.web_color = csscolors.hex2name(target_color)
            except:
                pass
            self.force_alpha = True
        elif convert in ('hex', 'hexa', 'ahex'):
            self.force_alpha = convert in ('hexa', 'ahex')
        elif convert in ('rgb', 'rgba'):
            self.convert_rgb = True
            self.force_alpha = convert == 'rgba'
        elif convert in ('hsl', 'hsla'):
            self.convert_hsl = True
            self.force_alpha = convert == 'hsla'

    def replacement(self, m):
        """See if match is a convert replacement of an existing color."""

        found = True
        if m.group('webcolors'):
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
        elif m.group('hexa') and self.use_argb:
            self.region = sublime.Region(m.start('hexa') + self.start, m.end('hexa') + self.start)
            content = m.group('hexa_content')
            self.alpha_hex = content[0:2] if len(content) > 4 else content[0:1] * 2
            self.alpha = util.fmt_float(float(int(self.alpha_hex, 16)) / 255.0, 3)
        elif m.group('hexa'):
            self.region = sublime.Region(m.start('hexa') + self.start, m.end('hexa') + self.start)
            content = m.group('hexa_content')
            self.alpha_hex = content[-2:] if len(content) > 4 else content[-1:] * 2
            self.alpha = util.fmt_float(float(int(self.alpha_hex, 16)) / 255.0, 3)
        elif m.group('hex'):
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
        elif m.group('rgb'):
            self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
        elif m.group('rgba'):
            self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
            content = [x.strip() for x in m.group('rgba_content').split(',')]
            self.alpha = content[3]
            self.alpha_hex = "%02x" % util.round_int(float(self.alpha) * 255.0)
        elif m.group('hsl'):
            self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
        elif m.group('hsla'):
            self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
            content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
            self.alpha = content[3]
            self.alpha_hex = "%02x" % util.round_int(float(self.alpha) * 255.0)
        else:
            found = False
        return found

    def completion(self, m):
        """See if match is completing an color."""

        found = True
        if m.group('hash'):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
        elif m.group('rgb_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
        elif m.group('rgba_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('rgba_open') + self.start, m.end('rgba_open') + self.start + offset)
            self.alpha = '1'
            self.alpha_hex = 'ff'
        elif m.group('hsl_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
        elif m.group('hsla_open'):
            self.offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hsla_open') + self.start, m.end('hsla_open') + self.start + offset)
            self.alpha = '1'
            self.alpha_hex = 'ff'
        else:
            found = False
        return found

    def convert_alpha(self):
        """Setup conversion alpha."""

        if self.force_alpha and self.alpha is None:
            self.alpha = '1'
            self.alpha_hex = 'ff'
        elif not self.force_alpha:
            self.alpha = None
            self.alpha_hex = None

    def calc(self):
        """Calculate how we are to insert the target color."""

        bfr = self.view.substr(sublime.Region(self.start, self.end))
        ref = self.point - self.start
        found = False

        for m in util.COLOR_ALL_RE.finditer(bfr):
            if ref >= m.start(0) and ref < m.end(0):
                found = self.replacement(m)
            elif ref == m.end(0):
                found = self.completion(m)
            elif ref < m.start(0):
                break

            if found:
                break

        self.convert_alpha()

        return found


class PickerInsertCalc(object):
    """Calculate and insert color."""

    def __init__(self, view, point):
        """Initialize insertion object."""

        self.view = view
        self.region = sublime.Region(point)
        self.start = point - 50
        self.end = point + 50
        self.point = point
        visible = self.view.visible_region()
        if self.start < visible.begin():
            self.start = visible.begin()
        if self.end > visible.end():
            self.end = visible.end()

    def replacement(self, m):
        """See if match is a replacement of an existing color."""

        found = True
        if m.group('webcolors'):
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
        elif m.group('hexa'):
            self.region = sublime.Region(m.start('hexa') + self.start, m.end('hexa') + self.start)
        elif m.group('hex'):
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
        elif m.group('rgb'):
            self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
        elif m.group('rgba'):
            self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
        elif m.group('hsl'):
            self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
        elif m.group('hsla'):
            self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
        else:
            found = False
        return found

    def completion(self, m):
        """See if match is completing an color."""

        found = True
        if m.group('hash'):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
        elif m.group('rgb_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
        elif m.group('rgba_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(
                m.start('rgba_open') + self.start, m.end('rgba_open') + self.start + offset
            )
        elif m.group('hsl_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
        elif m.group('hsla_open'):
            self.offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(
                m.start('hsla_open') + self.start, m.end('hsla_open') + self.start + offset
            )
        else:
            found = False
        return found

    def calc(self):
        """Calculate how we are to insert the target color."""

        bfr = self.view.substr(sublime.Region(self.start, self.end))
        ref = self.point - self.start
        found = False

        for m in util.COLOR_ALL_RE.finditer(bfr):
            if ref >= m.start(0) and ref < m.end(0):
                found = self.replacement(m)
            elif ref == m.end(0):
                found = self.completion(m)
            elif ref < m.start(0):
                break
            if found:
                break

        return found
