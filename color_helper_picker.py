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
from ColorHelper.multiconf import get as qualify_settings

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

SPACER = '#00000000'
OUTER_BORDER = '#fefefeff'
INNER_BORDER = '#333333ff'


class ColorHelperPickerCommand(sublime_plugin.TextCommand):
    """Experimental color picker."""

    def get_color_map_square(self):
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
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                html_colors.append(
                    [
                        mdpopups.color_box(
                            [SPACER], border_size=0,
                            height=self.height, width=(self.width * (6 if self.hex_map else 5)),
                            check_size=check_size, alpha=True
                        )
                    ]
                )
                for x in range(0, 15):
                    rgba.fromhls(h, l, s)
                    color = rgba.get_rgba()
                    kwargs = {
                        "border_size": 2, "height": self.height, "width": self.width,
                        "check_size": check_size
                    }

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
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                h, lum, s = rgba.tohls()
                rgba.fromhls(h, l, s)
                color = rgba.get_rgba()
                kwargs = {"border_size": 2, "height": self.height, "width": self.width, "check_size": check_size}

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
        self.template_vars['color_picker'] = color_map

    def get_color_map_hex(self):
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
            count = 0
            check_size = self.check_size(self.height)

            for row in color_map_data:
                html_colors.append('<span class="%scolor-map-row">' % util.LEGACY_CLASS)
                if padding:
                    pad = mdpopups.color_box(
                        [SPACER], border_size=0,
                        height=self.height, width=padding, check_size=check_size, alpha=True
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
                                border_size=2, height=self.height, width=self.width,
                                check_size=check_size
                            )
                        )
                    )
                html_colors.append('</span><br>')
                if count == 6:
                    decrement = False
                if decrement:
                    padding -= int(self.width / 2)
                else:
                    padding += int(self.width / 2)
                count += 1
            html_colors.append('\n\n')
            color_map = ''.join(html_colors)
        self.template_vars['color_picker'] = color_map

    def get_current_color(self):
        """Get current color."""

        check_size = self.check_size(self.height)
        html = (
            '<span class="%scurrent-color">%s</span>' % (
                util.LEGACY_CLASS,
                mdpopups.color_box(
                    [SPACER], border_size=0,
                    height=self.height, width=(self.width * (6 if self.hex_map else 5)),
                    check_size=check_size, alpha=True
                ) +
                mdpopups.color_box(
                    [self.color], OUTER_BORDER, INNER_BORDER,
                    border_size=2, height=self.height, width=self.width * (13 if self.hex_map else 16),
                    check_size=check_size
                )
            )
        )
        self.template_vars['current_color'] = html

    def get_css_color_names(self):
        """Get CSS color names."""

        check_size = self.check_size(self.box_height)
        html = []
        for name in sorted(csscolors.name2hex_map):
            color = util.RGBA(csscolors.name2hex(name)).get_rgba()

            html.append(
                '[%s](%s) %s<br>' % (
                    mdpopups.color_box(
                        [color], OUTER_BORDER, INNER_BORDER,
                        border_size=2, height=self.box_height, width=self.box_height * 8, check_size=check_size
                    ),
                    color,
                    name
                )
            )
        self.template_vars['channel_names'] = ''.join(html)

    def get_hires_color_channel(self, color_filter):
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
        check_size = self.check_size(self.box_height)
        html = []
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
            html.append(
                '[%s](%s) %s<br>' % (
                    mdpopups.color_box(
                        [color], OUTER_BORDER, INNER_BORDER,
                        border_size=2, height=self.box_height, width=self.box_height * 8, check_size=check_size
                    ),
                    color,
                    label
                )
            )
        self.template_vars['channel_hires'] = ''.join(html)

    def get_channel(self, channel, label, minimum, maximum, color_filter):
        """Get color channel."""

        rgba1 = util.RGBA(self.color)
        rgba2 = util.RGBA(self.color)
        html = []
        html.append('<span class="%schannel"><a href="hirespick:%s">%s:</a>' % (util.LEGACY_CLASS, color_filter, label))
        temp = []
        count = 12
        check_size = self.check_size(self.height)
        while count:
            getattr(rgba1, color_filter)(minimum)
            kwargs = {"border_size": 2, "height": self.height, "width": self.width, "check_size": check_size}
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
        html += reversed(temp)
        html.append(
            '[%s](%s)' % (
                mdpopups.color_box(
                    [self.color], OUTER_BORDER, INNER_BORDER,
                    border_size=2, height=self.height_big, width=self.width, check_size=check_size
                ),
                self.color
            )
        )
        count = 12
        while count:
            getattr(rgba2, color_filter)(maximum)
            kwargs = {"border_size": 2, "height": self.height, "width": self.width, "check_size": check_size}
            html.append(
                '[%s](%s)' % (
                    mdpopups.color_box(
                        [rgba2.get_rgba()], OUTER_BORDER, INNER_BORDER,
                        **kwargs
                    ),
                    rgba2.get_rgba()
                )
            )
            count -= 1
        html.append('</span><br>')
        self.template_vars[channel] = ''.join(html)

    def compress_hex_color(self, color):
        """Compress hex color if possible."""

        if self.compress_hex:
            color = util.compress_hex(color)
        return color

    def get_color_info(self):
        """Get color info."""

        rgba = util.RGBA(self.color)
        self.template_vars['rgb_r'] = rgba.r
        self.template_vars['rgb_g'] = rgba.g
        self.template_vars['rgb_b'] = rgba.b
        self.template_vars['alpha'] = self.alpha
        h, l, s = rgba.tohls()
        self.template_vars['hsl_h'] = util.fmt_float(h * 360.0)
        self.template_vars['hsl_l'] = util.fmt_float(l * 100.0)
        self.template_vars['hsl_s'] = util.fmt_float(s * 100.0)
        h, w, b = rgba.tohwb()
        self.template_vars['hwb_h'] = util.fmt_float(h * 360.0)
        self.template_vars['hwb_w'] = util.fmt_float(w * 100.0)
        self.template_vars['hwb_b'] = util.fmt_float(b * 100.0)

        if self.web_color and 'webcolors' in self.allowed_colors:
            self.template_vars['webcolor_info'] = True
            self.template_vars['webcolor_value'] = self.web_color
        if 'hex' in self.allowed_colors or 'hex_compressed' in self.allowed_colors:
            color = self.color[:-2].lower()
            self.template_vars['hex_info'] = True
            self.template_vars['hex_link'] = self.compress_hex_color(color)
            self.template_vars['hex_display'] = color
        if (
            ('hexa' in self.allowed_colors or 'hexa_compressed' in self.allowed_colors) and
            (self.use_hex_argb is None or self.use_hex_argb is False)
        ):
            color = self.color.lower()
            self.template_vars['hexa_info'] = True
            self.template_vars['hexa_link'] = self.compress_hex_color(color)
            self.template_vars['hexa_display'] = color[:-2]
            self.template_vars['hexa_alpha'] = color[-2:]
        if (
            ('hexa' in self.allowed_colors or 'hexa_compressed') and
            (self.use_hex_argb is None or self.use_hex_argb is True)
        ):
            color = '#' + (self.color[-2:] + self.color[1:-2]).lower()
            self.template_vars['ahex_info'] = True
            self.template_vars['ahex_link'] = self.compress_hex_color(color)
            self.template_vars['ahex_alpha'] = color[:-2]
            self.template_vars['ahex_display'] = color[1:-2]
        if 'rgb' in self.allowed_colors:
            self.template_vars['rgb_info'] = True
        if 'rgba' in self.allowed_colors:
            self.template_vars['rgba_info'] = True
        if 'hsl' in self.allowed_colors:
            self.template_vars['hsl_info'] = True
        if 'hsla' in self.allowed_colors:
            self.template_vars['hsla_info'] = True
        if 'hwb' in self.allowed_colors:
            self.template_vars['hwb_info'] = True
        if 'hwba' in self.allowed_colors:
            self.template_vars['hwba_info'] = True

    def set_sizes(self):
        """Get sizes."""

        settings = sublime.load_settings('color_helper.sublime-settings')
        self.graphic_size = qualify_settings(settings, 'graphic_size', 'medium')
        self.line_height = util.get_line_height(self.view)
        top_pad = self.view.settings().get('line_padding_top', 0)
        bottom_pad = self.view.settings().get('line_padding_bottom', 0)
        # Sometimes we strangely get None
        if top_pad is None:
            top_pad = 0
        if bottom_pad is None:
            bottom_pad = 0
        self.box_height = self.line_height - int(top_pad + bottom_pad) - 6
        if DISTORTION_FIX:
            sizes = {
                "small": (10, 14, 16),
                "medium": (14, 18, 20),
                "large": (18, 22, 24)
            }
        else:
            sizes = {
                "small": (int(self.box_height * .85), int(self.box_height * .85), int(self.box_height * 1.0)),
                "medium": (int(self.box_height), int(self.box_height), int(self.box_height * 1.25)),
                "large": (int(self.box_height * 1.15), int(self.box_height * 1.15), int(self.box_height * 1.35))
            }
        self.height, self.width, self.height_big = sizes.get(
            self.graphic_size,
            sizes["medium"]
        )

    def check_size(self, height):
        """Get checkered size."""

        if DISTORTION_FIX:
            check_size = 2
        else:
            check_size = int((self.height - 4) / 4)
            if check_size < 2:
                check_size = 2
        return check_size

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
        self.template_vars = {
            "legacy": util.LEGACY_CLASS
        }
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

        if colornames:
            self.template_vars['color_names'] = True
            self.template_vars['cancel'] = self.color
            self.get_css_color_names()
        elif hirespick:
            self.template_vars['hires'] = True
            self.template_vars['cancel'] = self.color
            self.template_vars['hires_color'] = hirespick
            self.get_hires_color_channel(hirespick)
        else:
            self.template_vars['picker'] = True
            self.template_vars['cancel'] = 'cancel'
            if self.hex_map:
                self.get_color_map_hex()
            else:
                self.get_color_map_square()
            self.get_current_color()
            if hsl:
                self.get_channel('channel_1', 'H', -15, 15, 'hue')
                self.get_channel('channel_2', 'S', 0.975, 1.025, 'saturation')
                self.get_channel('channel_3', 'L', 0.975, 1.025, 'luminance')
            else:
                self.get_channel('channel_1', 'R', 0.975, 1.025, 'red')
                self.get_channel('channel_2', 'G', 0.975, 1.025, 'green')
                self.get_channel('channel_3', 'B', 0.975, 1.025, 'blue')
            self.get_channel('channel_alpha', 'A', 0.975, 1.025, 'alpha')

            self.template_vars['color_switch'] = 'rgb' if self.hsl else 'hsl'
            self.get_color_info()

        mdpopups.show_popup(
            self.view,
            sublime.load_resource('Packages/ColorHelper/panels/color-picker.html'),
            css=util.ADD_CSS,
            wrapper_class="color-helper content",
            max_width=1024, max_height=(500 if hirespick or colornames else 725),
            on_navigate=self.handle_href,
            template_vars=self.template_vars,
            nl2br=False
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
            view.settings().set('color_helper.no_auto', True)
            view.run_command(
                'color_helper_picker',
                {
                    "color": value, "allowed_colors": self.allowed_colors,
                    "use_hex_argb": self.use_hex_argb, "compress_hex": self.compress_hex,
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )
