"""
ColorHelper.

Copyright (c) 2015 - 2016 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import mdpopups
from mdpopups import colorbox
import sublime
import sublime_plugin
from ColorHelper.lib import csscolors
import ColorHelper.color_helper_util as util
import copy

DISTORTION_FIX = int(sublime.version()) < 3118

try:
    popupver = mdpopups.version()
except Exception:
    popupver = (0, 0, 0)

BORDER_MAP_SUPPORT = popupver >= (1, 3, 0)

color_map_data = [
    ['036', '369', '36c', '039', '009', '00c', '006'],
    ['066', '069', '09c', '06c', '03c', '00f', '33f', '339'],
    ['699', '099', '3cc', '0cf', '09f', '06f', '36f', '33c', '669'],
    ['396', '0c9', '0fc', '0ff', '3cf', '39f', '69f', '66f', '60f', '60c'],
    ['393', '0c6', '0f9', '6fc', '6ff', '6cf', '9cf', '99f', '96f', '93f', '90f'],
    ['060', '0c0', '0f0', '6f9', '9fc', 'cff', 'ccf', 'c9f', 'c6f', 'c3f', 'c0f', '90c'],
    ['030', '093', '3c3', '6f6', '9f9', 'cfc', 'fff', 'fcf', 'f9f', 'f6f', 'f0f', 'c0c', '606'],
    ['360', '090', '6f3', '9f6', 'cf9', 'ffc', 'fcc', 'f9c', 'f6c', 'f3c', 'c09', '939'],
    ['330', '690', '9f3', 'cf6', 'ff9', 'fc9', 'f99', 'f69', 'f39', 'c39', '909'],
    ['663', '9c0', 'cf3', 'ff6', 'fc6', 'f96', 'f66', 'f06', 'c69', '936'],
    ['996', 'cc0', 'ff0', 'fc0', 'f93', 'f60', 'ff5050', 'c06', '603'],
    ['963', 'c90', 'f90', 'c60', 'f30', 'f00', 'c00', '903'],
    ['630', '960', 'c30', '930', '900', '800000', '933']
]

color_map = None
color_map_size = False
color_map_style = None
line_height = None

LINK = '<a href="insert:%s" class="color-helper small">&gt;&gt;&gt;</a> '
WEB_COLOR = '''%s<span class="constant numeric">%s</span><br>'''
HEX_COLOR = '''%s<span class="support type">%s</span><br>'''
HEXA_COLOR = '''%s<span class="support type">%s</span><span class="support type color-helper alpha">%s</span><br>'''
AHEX_COLOR = '''%s\
<span class="support type">%s</span>\
<span class="support type color-helper alpha">%s</span>\
<span class="support type">%s</span>
'''
RGB_COLOR = '''%s<span class="keyword">rgb</span>(<span class="constant numeric">%d, %d, %d</span>)<br>'''
RGBA_COLOR = '''%s<span class="keyword">rgba</span>(<span class="constant numeric">%d, %d, %d, %s</span>)<br>'''
HSL_COLOR = '''%s<span class="keyword">hsl</span>(<span class="constant numeric">%s, %s%%, %s%%</span>)<br>'''
HSLA_COLOR = '''%s<span class="keyword">hsla</span>(<span class="constant numeric">%s, %s%%, %s%%, %s</span>)<br>'''
HWB_COLOR = '''%s<span class="keyword">hwb</span>(<span class="constant numeric">%s, %s%%, %s%%</span>)<br>'''
HWBA_COLOR = '''%s<span class="keyword">hwb</span>(<span class="constant numeric">%s, %s%%, %s%%, %s</span>)<br>'''

RGB_INSERT = 'rgb(%d, %d, %d)'
RGBA_INSERT = 'rgba(%d, %d, %d, %s)'
HSL_INSERT = 'hsl(%s, %s%%, %s%%)'
HSLA_INSERT = 'hsla(%s, %s%%, %s%%, %s)'
HWB_INSERT = 'hwb(%s, %s%%, %s%%)'
HWBA_INSERT = 'hwb(%s, %s%%, %s%%, %s)'

SPACER = '#00000000'
OUTER_BORDER = '#fefefeff'
INNER_BORDER = '#333333ff'


class ColorHelperPickerCommand(sublime_plugin.TextCommand):
    """Experimental color picker."""

    def get_color_map_square(self, text):
        """Get a square variant of the color map."""

        global color_map
        global color_map_size
        global color_map_style
        global line_height

        if (
            color_map is None or
            self.graphic_size != color_map_size or
            self.line_height != line_height or
            color_map_style != "square"
        ):
            color_map_size = self.graphic_size
            color_map_style = "square"
            line_height = self.line_height

            html_colors = []

            rgba = util.RGBA()
            h = 0
            s = 0.9
            l = 0.9
            hfac = 15.0 / 360.0
            lfac = 8.0 / 100.0
            for y in range(0, 11):
                html_colors.append(
                    [
                        mdpopups.color_box(
                            [SPACER], border_size=0,
                            height=self.height, width=(self.width * (6 if self.hex_map else 5)), alpha=True
                        )
                    ]
                )
                for x in range(0, 15):
                    rgba.fromhls(h, l, s)
                    color = rgba.get_rgba()
                    kwargs = {"border_size": 2, "height": self.height, "width": self.width}

                    if BORDER_MAP_SUPPORT:
                        if y == 0 and x == 0:
                            border_map = colorbox.TOP | colorbox.LEFT
                        elif y == 0 and x == 14:
                            border_map = colorbox.TOP | colorbox.RIGHT
                        elif y == 0:
                            border_map = colorbox.TOP
                        elif y == 10 and x == 0:
                            border_map = colorbox.BOTTOM | colorbox.LEFT
                        elif y == 10 and x == 14:
                            border_map = colorbox.BOTTOM | colorbox.RIGHT
                        elif y == 10:
                            border_map = colorbox.BOTTOM
                        elif x == 0:
                            border_map = colorbox.LEFT
                        elif x == 14:
                            border_map = colorbox.RIGHT
                        else:
                            border_map = 0
                        kwargs["border_map"] = border_map

                    html_colors[-1].append(
                        '<a href="%s">%s</a>' % (
                            color, mdpopups.color_box(
                                [color], OUTER_BORDER, INNER_BORDER,
                                **kwargs
                            )
                        )
                    )
                    h += hfac
                h = 0
                l -= lfac

            l = 1.0
            lfac = 10.0 / 100.0
            rgba.r = 255.0
            rgba.g = 255.0
            rgba.b = 255.0
            for y in range(0, 11):
                h, lum, s = rgba.tohls()
                rgba.fromhls(h, l, s)
                color = rgba.get_rgba()
                kwargs = {"border_size": 2, "height": self.height, "width": self.width}

                if BORDER_MAP_SUPPORT:
                    if y == 0:
                        border_map = 0xb
                    elif y == 10:
                        border_map = 0xe
                    else:
                        border_map = 0xa
                    kwargs["border_map"] = border_map

                html_colors[y].append(
                    '<a href="%s">%s</a>' % (
                        color, mdpopups.color_box(
                            [color], OUTER_BORDER, INNER_BORDER,
                            **kwargs
                        )
                    )
                )
                l -= lfac

            color_map = ''.join(['<span>%s</span><br>' % ''.join([y1 for y1 in x1]) for x1 in html_colors]) + '\n\n'
        text.append(color_map)

    def get_color_map_hex(self, text):
        """Get color wheel."""

        global color_map
        global color_map_size
        global color_map_style
        global line_height

        if (
            color_map is None or
            self.graphic_size != color_map_size or
            self.line_height != line_height or
            color_map_style != "hex"
        ):
            color_map_size = self.graphic_size
            line_height = self.line_height
            color_map_style = "hex"
            padding = (self.width * 9)
            decrement = True
            html_colors = []
            for row in color_map_data:
                html_colors.append('<span class="color-helper color-map-row">')
                if padding:
                    pad = mdpopups.color_box(
                        [SPACER], border_size=0,
                        height=self.height, width=padding, check_size=2, alpha=True
                    )
                    html_colors.append(pad)
                for color in row:
                    if len(self.color) == 3:
                        color = '#' + ''.join([c * 2 for c in color]) + 'ff'
                    else:
                        color = '#' + color + 'ff'
                    html_colors.append(
                        '<a href="%s">%s</a>' % (
                            color, mdpopups.color_box(
                                [color], OUTER_BORDER, INNER_BORDER,
                                border_size=2, height=self.height, width=self.width
                            )
                        )
                    )
                html_colors.append('</span><br>')
                if padding == 6 * self.width:
                    decrement = False
                if decrement:
                    padding -= int(self.width / 2)
                else:
                    padding += int(self.width / 2)
            html_colors.append('\n\n')
            color_map = ''.join(html_colors)
        text.append(color_map)

    def get_current_color(self, text):
        """Get current color."""

        text.append(
            '<span class="color-helper current-color">%s</span>\n\n' % (
                mdpopups.color_box(
                    [SPACER], border_size=0,
                    height=self.height, width=(self.width * (6 if self.hex_map else 5)), check_size=2, alpha=True
                ) +
                mdpopups.color_box(
                    [self.color], OUTER_BORDER, INNER_BORDER,
                    border_size=2, height=self.height, width=self.width * (13 if self.hex_map else 16), check_size=2
                )
            )
        )

    def get_css_color_names(self, text):
        """Get CSS color names."""

        for name in sorted(csscolors.name2hex_map):
            color = util.RGBA(csscolors.name2hex(name)).get_rgba()

            text.append(
                '[%s](%s) %s\n' % (
                    mdpopups.color_box(
                        [color], OUTER_BORDER, INNER_BORDER,
                        border_size=2, height=self.height, width=self.width * 13, check_size=2
                    ),
                    color,
                    name
                )
            )

    def get_hires_color_channel(self, text, color_filter):
        """Get get a list of all colors within range."""

        ranges = {
            "red": (0, 255),
            "green": (0, 255),
            "blue": (0, 255),
            "alpha": (0, 255),
            "hue": (0, 360),
            "saturation": (0, 100),
            "luminance": (0, 100)
        }

        rgba = util.RGBA(self.color)
        h, l, s = rgba.tohls()
        minimum, maximum = ranges[color_filter]
        for x in range(minimum, maximum + 1):
            if color_filter == 'red':
                rgba.r = x
                label = str(x)
            elif color_filter == 'green':
                rgba.g = x
                label = str(x)
            elif color_filter == 'blue':
                rgba.b = x
                label = str(x)
            elif color_filter == 'alpha':
                rgba.a = x
                label = util.fmt_float(rgba.a * mdpopups.rgba.RGB_CHANNEL_SCALE, 3)
            elif color_filter == 'hue':
                h = x * mdpopups.rgba.HUE_SCALE
                rgba.fromhls(h, l, s)
                label = str(x)
            elif color_filter == 'saturation':
                s = x * 0.01
                rgba.fromhls(h, l, s)
                label = str(x)
            elif color_filter == 'luminance':
                l = x * 0.01
                rgba.fromhls(h, l, s)
                label = str(x)
            color = rgba.get_rgba()
            text.append(
                '[%s](%s) %s\n' % (
                    mdpopups.color_box(
                        [color], OUTER_BORDER, INNER_BORDER,
                        border_size=2, height=self.height, width=self.width * 13, check_size=2
                    ),
                    color,
                    label
                )
            )

    def get_channel(self, text, label, minimum, maximum, color_filter):
        """Get color channel."""

        rgba1 = util.RGBA(self.color)
        rgba2 = util.RGBA(self.color)
        text.append('<span class="color-helper channel"><a href="hirespick:%s">%s:</a>' % (color_filter, label))
        temp = []
        count = 12
        while count:
            getattr(rgba1, color_filter)(minimum)
            kwargs = {"border_size": 2, "height": self.height, "width": self.width, "check_size": 2}
            temp.append(
                '[%s](%s)' % (
                    mdpopups.color_box(
                        [rgba1.get_rgba()], OUTER_BORDER, INNER_BORDER,
                        **kwargs
                    ),
                    rgba1.get_rgba()
                )
            )
            count -= 1
        text += reversed(temp)
        text.append(
            '[%s](%s)' % (
                mdpopups.color_box(
                    [self.color], OUTER_BORDER, INNER_BORDER,
                    border_size=2, height=self.height_big, width=self.width, check_size=2
                ),
                self.color
            )
        )
        count = 12
        while count:
            getattr(rgba2, color_filter)(maximum)
            kwargs = {"border_size": 2, "height": self.height, "width": self.width, "check_size": 2}
            text.append(
                '[%s](%s)' % (
                    mdpopups.color_box(
                        [rgba2.get_rgba()], OUTER_BORDER, INNER_BORDER,
                        **kwargs
                    ),
                    rgba2.get_rgba()
                )
            )
            count -= 1
        text.append('</span>\n\n')

    def compress_hex_color(self, color):
        """Compress hex color if possible."""

        if self.compress_hex:
            color = util.compress_hex(color)
        return color

    def get_color_info(self, text):
        """Get color info."""

        rgba = util.RGBA(self.color)

        if self.web_color and 'webcolors' in self.allowed_colors:
            text.append(WEB_COLOR % (LINK % self.web_color, self.web_color))
        if 'hex' in self.allowed_colors or 'hex_compressed' in self.allowed_colors:
            color = self.color[:-2].lower()
            text.append(HEX_COLOR % (LINK % self.compress_hex_color(color), color))
        if (
            ('hexa' in self.allowed_colors or 'hexa_compressed' in self.allowed_colors) and
            (self.use_hex_argb is None or self.use_hex_argb is False)
        ):
            color = self.color.lower()
            text.append(HEXA_COLOR % (LINK % self.compress_hex_color(color), color[:-2], color[-2:]))
        if (
            ('hexa' in self.allowed_colors or 'hexa_compressed') and
            (self.use_hex_argb is None or self.use_hex_argb is True)
        ):
            color = '#' + (self.color[-2:] + self.color[1:-2]).lower()
            text.append(AHEX_COLOR % (LINK % self.compress_hex_color(color), color[0], color[-2:], color[1:-2]))
        if 'rgb' in self.allowed_colors:
            color = RGB_INSERT % (rgba.r, rgba.g, rgba.b)
            text.append(RGB_COLOR % (LINK % color, rgba.r, rgba.g, rgba.b))
        if 'rgba' in self.allowed_colors:
            color = RGBA_INSERT % (rgba.r, rgba.g, rgba.b, self.alpha)
            text.append(RGBA_COLOR % (LINK % color, rgba.r, rgba.g, rgba.b, self.alpha))
        h, l, s = rgba.tohls()
        if 'hsl' in self.allowed_colors:
            color = HSL_INSERT % (util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0))
            text.append(
                HSL_COLOR % (
                    LINK % color, util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0)
                )
            )
        if 'hsla' in self.allowed_colors:
            color = HSLA_INSERT % (
                util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0), self.alpha
            )
            text.append(
                HSLA_COLOR % (
                    LINK % color, util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0),
                    self.alpha
                )
            )
        h, w, b = rgba.tohwb()
        if 'hwb' in self.allowed_colors:
            color = HWB_INSERT % (util.fmt_float(h * 360.0), util.fmt_float(w * 100.0), util.fmt_float(b * 100.0))
            text.append(
                HWB_COLOR % (
                    LINK % color, util.fmt_float(h * 360.0), util.fmt_float(w * 100.0), util.fmt_float(b * 100.0)
                )
            )
        if 'hwba' in self.allowed_colors:
            color = HWBA_INSERT % (
                util.fmt_float(h * 360.0), util.fmt_float(w * 100.0), util.fmt_float(b * 100.0), self.alpha
            )
            text.append(
                HWBA_COLOR % (
                    LINK % color, util.fmt_float(h * 360.0), util.fmt_float(w * 100.0), util.fmt_float(b * 100.0),
                    self.alpha
                )
            )

    def set_sizes(self):
        """Get sizes."""

        settings = sublime.load_settings('color_helper.sublime-settings')
        self.graphic_size = settings.get('graphic_size', "medium")
        self.line_height = int(self.view.line_height())
        padding = int(self.view.settings().get('line_padding_top', 0))
        padding += int(self.view.settings().get('line_padding_bottom', 0))
        box_height = self.line_height - padding - 6
        if DISTORTION_FIX:
            sizes = {
                "small": (10, 14, 16),
                "medium": (14, 18, 20),
                "large": (18, 22, 24)
            }
        else:
            sizes = {
                "small": (int(box_height * .85), int(box_height * .85), int(box_height * 1.0)),
                "medium": (int(box_height), int(box_height), int(box_height * 1.25)),
                "large": (int(box_height * 1.15), int(box_height * 1.15), int(box_height * 1.35))
            }
        self.height, self.width, self.height_big = sizes.get(
            self.graphic_size,
            sizes["medium"]
        )

    def run(
        self, edit, color='#ffffff', allowed_colors=util.ALL, use_hex_argb=None,
        compress_hex=False, hsl=False, hirespick=None, colornames=False,
        on_done=None, on_cancel=None
    ):
        """Run command."""

        self.on_done = on_done
        self.on_cancel = on_cancel
        self.use_hex_argb = use_hex_argb
        self.compress_hex = compress_hex
        self.allowed_colors = allowed_colors
        self.hex_map = sublime.load_settings('color_helper.sublime-settings').get('use_hex_color_picker', True)
        rgba = util.RGBA(color)
        self.set_sizes()
        self.hsl = hsl
        self.color = rgba.get_rgba()
        self.alpha = util.fmt_float(float(int(self.color[-2:], 16)) / 255.0, 3)
        try:
            self.web_color = csscolors.hex2name(rgba.get_rgb())
        except Exception:
            self.web_color = None

        text = []
        if colornames:
            text.append('[cancel](%s){: .color-helper .small} ' % self.color)
            text.append('\n\n## CSS Color Names\n\n')
            self.get_css_color_names(text)
        elif hirespick:
            text.append('[cancel](%s){: .color-helper .small} ' % self.color)
            text.append('\n\n## %s\n\n' % hirespick)
            self.get_hires_color_channel(text, hirespick)
        else:
            text.append('[cancel](cancel){: .color-helper .small} ')
            text.append('[CSS color names](colornames){: .color-helper .small} ')
            text.append('[enter new color](edit){: .color-helper .small}\n\n')
            if self.hex_map:
                self.get_color_map_hex(text)
            else:
                self.get_color_map_square(text)
            self.get_current_color(text)
            text.append('\n\n---\n\n')
            if hsl:
                self.get_channel(text, 'H', -15, 15, 'hue')
                self.get_channel(text, 'S', 0.975, 1.025, 'saturation')
                self.get_channel(text, 'L', 0.975, 1.025, 'luminance')
            else:
                self.get_channel(text, 'R', 0.975, 1.025, 'red')
                self.get_channel(text, 'G', 0.975, 1.025, 'green')
                self.get_channel(text, 'B', 0.975, 1.025, 'blue')
            self.get_channel(text, 'A', 0.975, 1.025, 'alpha')
            text.append(
                '[switch to %s](%s){: .color-helper .small}\n' % (
                    'rgb' if self.hsl else 'hsl', 'rgb' if self.hsl else 'hsl'
                )
            )
            text.append('\n\n---\n\n')
            self.get_color_info(text)

        md = mdpopups.md2html(self.view, ''.join(text))
        mdpopups.show_popup(
            self.view, '<div class="color-helper content">%s</div>' % md,
            css=util.ADD_CSS,
            max_width=1024, max_height=(500 if hirespick or colornames else 725),
            on_navigate=self.handle_href
        )

    def handle_href(self, href):
        """Handle href."""

        hires = None
        hsl = self.hsl
        colornames = False
        if href in ('hsl', 'rgb'):
            hsl = href == 'hsl'
            color = self.color
        elif href.startswith('insert'):
            color = href.split(':')[1]
        elif href.startswith('hirespick'):
            hires = href.split(':')[1]
            color = self.color
        elif href == "colornames":
            color = self.color
            colornames = True
        elif href == 'edit':
            color = self.color
        else:
            color = href
        if href == 'cancel':
            mdpopups.hide_popup(self.view)
            if self.on_cancel is not None:
                call = self.on_cancel.get('command', 'color_helper')
                args = self.on_cancel.get('args', {})
                self.view.run_command(call, args)
        elif href == 'edit':
            mdpopups.hide_popup(self.view)
            self.view.window().run_command(
                'color_helper_picker_panel',
                {
                    "color": color, "allowed_colors": self.allowed_colors,
                    "use_hex_argb": self.use_hex_argb, "compress_hex": self.compress_hex,
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )
        elif href.startswith('insert'):
            mdpopups.hide_popup(self.view)
            if self.on_done is not None:
                call = self.on_done.get('command', 'color_helper')
                args = copy.deepcopy(self.on_done.get('args', {}))
                args['color'] = color
                self.view.run_command(call, args)
        else:
            self.view.run_command(
                'color_helper_picker',
                {
                    "color": color, "allowed_colors": self.allowed_colors,
                    "use_hex_argb": self.use_hex_argb, "compress_hex": self.compress_hex,
                    "hsl": hsl, "hirespick": hires, "colornames": colornames,
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )


class ColorHelperPickerPanel(sublime_plugin.WindowCommand):
    """Open color picker with color from panel."""

    def run(
        self, color="#ffffffff", allowed_colors=util.ALL,
        use_hex_argb=None, compress_hex=False,
        on_done=None, on_cancel=None
    ):
        """Run command."""

        self.on_done = on_done
        self.on_cancel = on_cancel
        self.compress_hex = compress_hex
        self.use_hex_argb = use_hex_argb
        self.allowed_colors = allowed_colors
        view = self.window.show_input_panel(
            '(hex) #RRGGBBAA', color, self.handle_value, None, None
        )
        view.sel().clear()
        view.sel().add(sublime.Region(0, view.size()))

    def handle_value(self, value):
        """Open color picker."""

        value = value.strip()
        try:
            value = util.RGBA(value).get_rgba()
        except Exception:
            value = "#ffffffff"
        view = self.window.active_view()
        if view is not None:
            view.run_command(
                'color_helper_picker',
                {
                    "color": value, "allowed_colors": self.allowed_colors,
                    "use_hex_argb": self.use_hex_argb, "compress_hex": self.compress_hex,
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )
