"""Calculate Insertion of color."""
import sublime
from ColorHelper.lib import csscolors
import ColorHelper.color_helper_util as util


class InsertCalc(object):
    """Convert."""

    def __init__(self, view, point, target_color, convert, allowed_colors, use_hex_argb):
        """Initialize."""

        self.convert_rgb = False
        self.convert_hsl = False
        self.convert_hwb = False
        self.convert_gray = False
        self.allowed_colors = allowed_colors
        self.alpha = None
        self.force_alpha = False
        self.use_hex_argb = use_hex_argb
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
        elif convert in ('gray', 'graya'):
            self.convert_gray = True
            self.force_alpha = convert == 'graya'
        elif convert in ('hex', 'hexa', 'ahex'):
            self.force_alpha = convert in ('hexa', 'ahex')
        elif convert in ('rgb', 'rgba'):
            self.convert_rgb = True
            self.force_alpha = convert == 'rgba'
        elif convert in ('hsl', 'hsla'):
            self.convert_hsl = True
            self.force_alpha = convert == 'hsla'
        elif convert in ('hwb', 'hwba'):
            self.convert_hwb = True
            self.force_alpha = convert == 'hwba'

    def replacement(self, m):
        """See if match is a convert replacement of an existing color."""

        found = True
        if m.group('webcolors') and 'webcolors' in self.allowed_colors:
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
        elif m.group('hexa') and self.use_hex_argb and 'hexa' in self.allowed_colors:
            self.region = sublime.Region(m.start('hexa') + self.start, m.end('hexa') + self.start)
            content = m.group('hexa_content')
            self.alpha_hex = content[0:2]
            self.alpha = util.fmt_float(float(int(self.alpha_hex, 16)) / 255.0, 3)
        elif m.group('hexa') and 'hexa' in self.allowed_colors:
            self.region = sublime.Region(m.start('hexa') + self.start, m.end('hexa') + self.start)
            content = m.group('hexa_content')
            self.alpha_hex = content[-2:]
            self.alpha = util.fmt_float(float(int(self.alpha_hex, 16)) / 255.0, 3)
        elif m.group('hex') and 'hex' in self.allowed_colors:
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
        elif m.group('hexa_compressed') and self.use_hex_argb and 'hexa_compressed' in self.allowed_colors:
            self.region = sublime.Region(m.start('hexa_compressed') + self.start, m.end('hexa_compressed') + self.start)
            content = m.group('hexa_compressed_content')
            self.alpha_hex = content[0:1] * 2
            self.alpha = util.fmt_float(float(int(self.alpha_hex, 16)) / 255.0, 3)
        elif m.group('hexa_compressed') and 'hexa_compressed' in self.allowed_colors:
            self.region = sublime.Region(m.start('hexa_compressed') + self.start, m.end('hexa_compressed') + self.start)
            content = m.group('hexa_compressed_content')
            self.alpha_hex = content[-1:] * 2
            self.alpha = util.fmt_float(float(int(self.alpha_hex, 16)) / 255.0, 3)
        elif m.group('hex_compressed') and 'hex_compressed' in self.allowed_colors:
            self.region = sublime.Region(m.start('hex_compressed') + self.start, m.end('hex_compressed') + self.start)
        elif m.group('rgb') and 'rgb' in self.allowed_colors:
            self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
        elif m.group('rgba') and 'rgba' in self.allowed_colors:
            self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
            content = [x.strip() for x in m.group('rgba_content').split(',')]
            temp = float(content[3])
            if temp < 0.0 or temp > 1.0:
                content[3] = util.fmt_float(util.clamp(float(temp), 0.0, 1.0), 3)
            self.alpha = content[3]
            self.alpha_hex = "%02x" % util.round_int(float(self.alpha) * 255.0)
        elif m.group('gray') and 'gray' in self.allowed_colors:
            self.region = sublime.Region(m.start('gray') + self.start, m.end('gray') + self.start)
        elif m.group('graya') and 'graya' in self.allowed_colors:
            self.region = sublime.Region(m.start('graya') + self.start, m.end('graya') + self.start)
            content = [x.strip() for x in m.group('graya_content').split(',')]
            if content[1].endswith('%'):
                content[1] = util.fmt_float(util.clamp(float(content[1].strip('%')), 0.0, 100.0) / 100.0, 3)
            else:
                temp = float(content[1])
                if temp < 0.0 or temp > 1.0:
                    content[1] = util.fmt_float(util.clamp(float(temp), 0.0, 1.0), 3)
            self.alpha = content[1]
            self.alpha_hex = "%02x" % util.round_int(float(self.alpha) * 255.0)
        elif m.group('hsl') and 'hsl' in self.allowed_colors:
            self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
        elif m.group('hsla') and 'hsla' in self.allowed_colors:
            self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
            content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
            temp = float(content[3])
            if temp < 0.0 or temp > 1.0:
                content[3] = util.fmt_float(util.clamp(float(temp), 0.0, 1.0), 3)
            self.alpha = content[3]
            self.alpha_hex = "%02x" % util.round_int(float(self.alpha) * 255.0)
        elif m.group('hwb') and 'hwb' in self.allowed_colors:
            self.region = sublime.Region(m.start('hwb') + self.start, m.end('hwb') + self.start)
        elif m.group('hwba') and 'hwba' in self.allowed_colors:
            self.region = sublime.Region(m.start('hwba') + self.start, m.end('hwba') + self.start)
            content = [x.strip().rstrip('%') for x in m.group('hwba_content').split(',')]
            temp = float(content[3])
            if temp < 0.0 or temp > 1.0:
                content[3] = util.fmt_float(util.clamp(float(temp), 0.0, 1.0), 3)
            self.alpha = content[3]
            self.alpha_hex = "%02x" % util.round_int(float(self.alpha) * 255.0)
        else:
            found = False
        return found

    def completion(self, m):
        """See if match is completing an color."""

        found = True
        if m.group('hash') and ('hex' in self.allowed_colors or 'hexa' in self.allowed_colors):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
        elif m.group('hash') and ('hex_compressed' in self.allowed_colors or 'hexa_compressed' in self.allowed_colors):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
        elif m.group('rgb_open') and 'rgb' in self.allowed_colors:
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
        elif m.group('rgba_open') and 'rgba' in self.allowed_colors:
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('rgba_open') + self.start, m.end('rgba_open') + self.start + offset)
            self.alpha = '1'
            self.alpha_hex = 'ff'
        elif m.group('gray_open') and ('gray' in self.allowed_colors or 'graya' in self.allowed_colors):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('gray_open') + self.start, m.end('gray_open') + self.start + offset)
        elif m.group('hsl_open') and 'hsl' in self.allowed_colors:
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
        elif m.group('hsla_open') and 'hsla' in self.allowed_colors:
            self.offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hsla_open') + self.start, m.end('hsla_open') + self.start + offset)
            self.alpha = '1'
            self.alpha_hex = 'ff'
        elif m.group('hwb_open') and ('hwb' in self.allowed_colors or 'hwba' in self.allowed_colors):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hwb_open') + self.start, m.end('hwb_open') + self.start + offset)
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

    def __init__(self, view, point, allowed_colors):
        """Initialize insertion object."""

        self.view = view
        self.region = sublime.Region(point)
        self.allowed_colors = allowed_colors
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
        if m.group('webcolors') and 'webcolors' in self.allowed_colors:
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
        elif m.group('hexa') and 'hexa' in self.allowed_colors:
            self.region = sublime.Region(m.start('hexa') + self.start, m.end('hexa') + self.start)
        elif m.group('hex') and 'hex' in self.allowed_colors:
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
        elif m.group('hexa_compressed') and 'hexa_compressed' in self.allowed_colors:
            self.region = sublime.Region(m.start('hexa_compressed') + self.start, m.end('hexa_compressed') + self.start)
        elif m.group('hex_compressed') and 'hex_compressed' in self.allowed_colors:
            self.region = sublime.Region(m.start('hex_compressed') + self.start, m.end('hex_compressed') + self.start)
        elif m.group('rgb') and 'rgb' in self.allowed_colors:
            self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
        elif m.group('rgba') and 'rgba' in self.allowed_colors:
            self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
        elif m.group('gray') and 'gray' in self.allowed_colors:
            self.region = sublime.Region(m.start('gray') + self.start, m.end('gray') + self.start)
        elif m.group('graya') and 'graya' in self.allowed_colors:
            self.region = sublime.Region(m.start('graya') + self.start, m.end('graya') + self.start)
        elif m.group('hsl') and 'hsl' in self.allowed_colors:
            self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
        elif m.group('hsla') and 'hsla' in self.allowed_colors:
            self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
        elif m.group('hwb') and 'hwb' in self.allowed_colors:
            self.region = sublime.Region(m.start('hwb') + self.start, m.end('hwb') + self.start)
        elif m.group('hwba') and 'hwba' in self.allowed_colors:
            self.region = sublime.Region(m.start('hwba') + self.start, m.end('hwba') + self.start)
        else:
            found = False
        return found

    def completion(self, m):
        """See if match is completing an color."""

        found = True
        if m.group('hash') and ('hex' in self.allowed_colors or 'hexa' in self.allowed_colors):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
        elif m.group('hash') and ('hex_copressed' in self.allowed_colors or 'hexa_copressed' in self.allowed_colors):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
        elif m.group('rgb_open') and 'rgb' in self.allowed_colors:
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
        elif m.group('rgba_open') and 'rgba' in self.allowed_colors:
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(
                m.start('rgba_open') + self.start, m.end('rgba_open') + self.start + offset
            )
        elif m.group('gray_open') and ('gray' in self.allowed_colors or 'graya' in self.allowed_colors):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(
                m.start('gray_open') + self.start, m.end('gray_open') + self.start + offset
            )
        elif m.group('hsl_open') and 'hsl' in self.allowed_colors:
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
        elif m.group('hsla_open') and 'hsla' in self.allowed_colors:
            self.offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(
                m.start('hsla_open') + self.start, m.end('hsla_open') + self.start + offset
            )
        elif m.group('hwb_open') and ('hwb' in self.allowed_colors or 'hwba' in self.allowed_colors):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            self.region = sublime.Region(m.start('hwb_open') + self.start, m.end('hwb_open') + self.start + offset)
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
