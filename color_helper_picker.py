"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import mdpopups
from mdpopups import colorbox
import sublime
import sublime_plugin
from coloraide.css import colorcss
from coloraide.css.colors import css_names
from . import color_helper_util as util
import copy
from .multiconf import get as qualify_settings

color_map = None
color_map_size = False
color_map_style = None
line_height = None
default_border = None
color_scale = None
last_saturation = None

SPACER = '#00000000'

BORDER_SIZE = 1


class ColorHelperPickerCommand(sublime_plugin.TextCommand):
    """Experimental color picker."""

    def get_spacer(self, width=1, height=1):
        """Get a spacer."""

        return mdpopups.color_box(
            [SPACER], border_size=0,
            height=self.height * height, width=self.width * width,
            check_size=self.check_size(self.height), alpha=True
        )

    def get_color_map_square(self):
        """Get a square variant of the color map."""

        global color_map
        global color_map_size
        global color_map_style
        global line_height
        global default_border
        global color_scale
        global last_saturation

        s = self.color.convert("hsl").saturation

        if (
            color_map is None or
            s != last_saturation or
            self.graphic_size != color_map_size or
            self.graphic_scale != color_scale or
            self.line_height != line_height or
            self.default_border != default_border or
            color_map_style != "square"
        ):
            color_map_size = self.graphic_size
            color_scale = self.graphic_scale
            color_map_style = "square"
            line_height = self.line_height
            default_border = self.default_border

            html_colors = []

            color = colorcss("hsl(0 {}% 90%)".format(s))
            hfac = 24.0
            lfac = 8.0
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                html_colors.append([self.get_spacer(width=5)])
                for x in range(0, 15):
                    # rgb = RGB(HSL("HSL({:f} {:f}% {:f}%)".format(h * 360.0, s * 100, l * 100)))
                    value = color.convert("srgb").to_string(hex_code=True, alpha=True)
                    kwargs = {
                        "border_size": BORDER_SIZE, "height": self.height, "width": self.width,
                        "check_size": check_size
                    }

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
                            color.to_string(), mdpopups.color_box(
                                [value], self.default_border,
                                **kwargs
                            )
                        )
                    )
                    color.hue = color.hue + hfac
                color.hue = 0.0
                color.lightness = color.lightness - lfac

            lfac = 10.0
            color = colorcss('hsl(0 0% 100%)')
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                value = color.convert("srgb").to_string(hex_code=True, alpha=True)
                kwargs = {
                    "border_size": BORDER_SIZE, "height": self.height, "width": self.width, "check_size": check_size
                }

                if y == 0:
                    border_map = 0xb
                elif y == 10:
                    border_map = 0xe
                else:
                    border_map = 0xa
                kwargs["border_map"] = border_map

                html_colors[y].append(
                    '<a href="%s">%s</a>' % (
                        color.to_string(), mdpopups.color_box(
                            [value], self.default_border,
                            **kwargs
                        )
                    )
                )
                color.lightness = color.lightness - lfac

            color_map = ''.join(['<span>%s</span><br>' % ''.join([y1 for y1 in x1]) for x1 in html_colors]) + '\n\n'
        self.template_vars['color_picker'] = color_map

    def get_current_color(self):
        """Get current color."""

        check_size = self.check_size(self.height)
        html = (
            '<span class="current-color">{}</span>'.format(
                self.get_spacer(width=5) +
                mdpopups.color_box(
                    [self.color.convert("srgb").to_string(hex_code=True, alpha=True)], self.default_border,
                    border_size=BORDER_SIZE, height=self.height * 2, width=self.width * 16,
                    check_size=check_size
                )
            )
        )
        self.template_vars['current_color'] = html

    def get_css_color_names(self):
        """Get CSS color names."""

        check_size = self.check_size(self.box_height)
        html = []
        for name in sorted(css_names.name2hex_map):
            color = colorcss(name)

            html.append(
                '[%s](%s) %s<br>' % (
                    mdpopups.color_box(
                        [color.to_string(hex_code=True)], self.default_border,
                        border_size=BORDER_SIZE, height=self.height, width=self.box_height * 8,
                        check_size=check_size
                    ),
                    color.to_string(),
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
            "alpha": (0, 100),
            "hue": (0, 360),
            "saturation": (0, 100),
            "lightness": (0, 100),
            "whiteness": (0, 100),
            "blackness": (0, 100)
        }

        minimum, maximum = ranges[color_filter]
        check_size = self.check_size(self.box_height)
        html = []
        color = self.color.clone()
        for x in range(minimum, maximum + 1):
            if color_filter == 'red':
                color.red = x / 255.0
                label = str(x)
            elif color_filter == 'green':
                color.green = x / 255.0
                label = str(x)
            elif color_filter == 'blue':
                color.blue = x / 255.0
                label = str(x)
            elif color_filter == 'alpha':
                color.alpha = x / 100.0
                label = "{:d}%".format(x)
            elif color_filter == 'hue':
                color.hue = x
                label = "{:d}deg".format(x)
            elif color_filter == 'saturation':
                color.saturation = x
                label = "{:d}%".format(x)
            elif color_filter == 'lightness':
                color.lightness = x
                label = "{:d}%".format(x)
            elif color_filter == "whiteness":
                color.whiteness = x
                label = "{:d}%".format(x)
            elif color_filter == "blackness":
                color.blackness = x
                label = "{:d}%".format(x)

            html.append(
                '[%s](%s) %s<br>' % (
                    mdpopups.color_box(
                        [color.convert("srgb").to_string(hex_code=True, alpha=True)], self.default_border,
                        border_size=BORDER_SIZE, height=self.height, width=self.box_height * 8,
                        check_size=check_size
                    ),
                    color.to_string(),
                    label
                )
            )
        self.template_vars['channel_hires'] = ''.join(html)

    def get_channel(self, channel, label, minimum, maximum, color_filter):
        """Get color channel."""

        html = []
        html.append('<span class="channel"><a href="hirespick:%s">%s:</a>' % (color_filter, label))
        temp = []
        count = 12
        check_size = self.check_size(self.height)
        clone = self.color.clone()

        mn = minimum
        first = True
        while count:
            coord = getattr(clone, color_filter) + mn
            setattr(clone, color_filter, coord)

            if not clone.in_gamut():
                temp.append(self.get_spacer(width=count))
                break
            elif color_filter == "alpha" and (coord < 0 or coord > 1.0):
                temp.append(self.get_spacer(width=count))
                break
            elif self.mode in ("hsl", "hwb") and color_filter == "hue" and (coord < 0 or coord > 360):
                temp.append(self.get_spacer(width=count))
                break
            else:
                border_map = colorbox.TOP | colorbox.BOTTOM | colorbox.LEFT
                if first:
                    border_map |= colorbox.RIGHT
                    first = False

                kwargs = {
                    "border_size": BORDER_SIZE, "height": self.height, "width": self.width, "check_size": check_size,
                    "border_map": border_map
                }

                temp.append(
                    '[%s](%s)' % (
                        mdpopups.color_box(
                            [clone.convert("srgb").to_string(hex_code=True, alpha=True)], self.default_border,
                            **kwargs
                        ),
                        clone.to_string()
                    )
                )
            clone.mutate(self.color)
            mn += minimum
            count -= 1
        html += reversed(temp)
        html.append(
            '[%s](%s)' % (
                mdpopups.color_box(
                    [self.color.convert("srgb").to_string(hex_code=True, alpha=True)], self.default_border,
                    border_size=BORDER_SIZE, height=self.height_big, width=self.width, check_size=check_size
                ),
                self.color.to_string()
            )
        )
        first = True
        count = 12
        mx = maximum

        clone.mutate(self.color)
        while count:
            coord = getattr(clone, color_filter) + mx
            setattr(clone, color_filter, coord)

            if not clone.in_gamut():
                html.append(self.get_spacer(width=count))
                break
            elif color_filter == "alpha" and (coord < 0 or coord > 1.0):
                html.append(self.get_spacer(width=count))
                break
            elif self.mode in ("hsl", "hwb") and color_filter == "hue" and (coord < 0 or coord > 360):
                html.append(self.get_spacer(width=count))
                break
            else:
                border_map = colorbox.TOP | colorbox.BOTTOM | colorbox.RIGHT
                if first:
                    border_map |= colorbox.LEFT
                    first = False

                kwargs = {
                    "border_size": BORDER_SIZE, "height": self.height, "width": self.width, "check_size": check_size,
                    "border_map": border_map
                }

                html.append(
                    '[%s](%s)' % (
                        mdpopups.color_box(
                            [clone.convert("srgb").to_string(hex_code=True, alpha=True)], self.default_border,
                            **kwargs
                        ),
                        clone.to_string()
                    )
                )
            clone.mutate(self.color)
            mx += maximum
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

        return

        all_space = "all" in self.space_separator_syntax
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
        self.template_vars['rgb_comma'] = not all_space and "rgb" not in self.space_separator_syntax
        self.template_vars['hsl_comma'] = not all_space and "hsl" not in self.space_separator_syntax
        self.template_vars['hwb_comma'] = not all_space and "hwb" not in self.space_separator_syntax

        if self.web_color and 'webcolors' in self.allowed_colors:
            self.template_vars['webcolor_info'] = True
            self.template_vars['webcolor_value'] = self.web_color
        if 'hex' in self.allowed_colors or 'hex_compressed' in self.allowed_colors:
            settings = sublime.load_settings('color_helper.sublime-settings')
            use_upper = settings.get("upper_case_hex", False)
            color = self.color[:-2].lower()
            self.template_vars['hex_info'] = True
            self.template_vars['hex_link'] = (
                self.compress_hex_color(color).upper() if use_upper else self.compress_hex_color(color)
            )
            self.template_vars['hex_display'] = color.upper() if use_upper else color
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
            (self.use_hex_argb is True)
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
        self.graphic_scale = qualify_settings(settings, 'graphic_scale', None)
        if not isinstance(self.graphic_scale, (int, float)):
            self.graphic_scale = None
        self.line_height = util.get_line_height(self.view)
        top_pad = self.view.settings().get('line_padding_top', 0)
        bottom_pad = self.view.settings().get('line_padding_bottom', 0)
        # Sometimes we strangely get None
        if top_pad is None:
            top_pad = 0
        if bottom_pad is None:
            bottom_pad = 0
        box_height = self.line_height - int(top_pad + bottom_pad) - 6
        if self.graphic_scale is not None:
            box_height = box_height * self.graphic_scale
            self.graphic_size = "small"
        small = max(box_height, 8)
        medium = max(box_height * 1.5, 8)
        large = max(box_height * 2, 8)
        self.box_height = int(small)
        sizes = {
            "small": (int(small), int(small), int(small + small / 4)),
            "medium": (int(medium), int(medium), int(medium + medium / 4)),
            "large": (int(large), int(large), int(large + large / 4))
        }
        self.height, self.width, self.height_big = sizes.get(
            self.graphic_size,
            sizes["medium"]
        )

    def check_size(self, height):
        """Get checkered size."""

        check_size = int((self.height - 4) / 4)
        if check_size < 2:
            check_size = 2
        return check_size

    def run(
        self, edit, color='#ffffff', allowed_colors=util.ALL, use_hex_argb=None,
        compress_hex=False, mode=None, hirespick=None, colornames=False,
        on_done=None, on_cancel=None, space_separator_syntax=None, **kwargs
    ):
        """Run command."""

        # Calculate image border.
        border_color = None
        settings = sublime.load_settings('color_helper.sublime-settings')
        border_color = settings.get('image_border_color')
        if border_color is not None:
            try:
                border_color = colorcss(border_color)
            except Exception:
                pass
        if border_color is None:
            border_color = colorcss(mdpopups.scope2style(self.view, '')['background']).convert("hsl")
            border_color.lightness = border_color.lightness + (20 if border_color.luminance() < 0.5 else 20)
        self.default_border = border_color.convert("srgb").to_string(hex_code=True, alpha=True)

        self.on_done = on_done
        self.on_cancel = on_cancel
        self.template_vars = {}

        self.original = colorcss(color)
        if mode is None or mode not in ("srgb", "hsl", "hwb"):
            if self.original.space() in ("srgb", "hsl", "hwb"):
                mode = self.original.space()
            else:
                mode = "srgb"
        self.color = self.original.convert(mode)
        if not self.color.in_gamut():
            self.color.fit_gamut()
        self.set_sizes()
        self.mode = mode

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
            self.get_color_map_square()
            self.get_current_color()
            if mode == "hsl":
                self.get_channel('channel_1', 'H', -5, 5, 'hue')
                self.get_channel('channel_2', 'S', -1, 1, 'saturation')
                self.get_channel('channel_3', 'L', -1, 1, 'lightness')
            elif mode == "hwb":
                self.get_channel('channel_1', 'H', -5, 5, 'hue')
                self.get_channel('channel_2', 'W', -1, 1, 'whiteness')
                self.get_channel('channel_3', 'B', -1, 1, 'blackness')
            else:
                self.get_channel('channel_1', 'R', -0.02, 0.02, 'red')
                self.get_channel('channel_2', 'G', -0.02, 0.02, 'green')
                self.get_channel('channel_3', 'B', -0.02, 0.02, 'blue')
            self.get_channel('channel_alpha', 'A', -0.02, 0.02, 'alpha')

            if mode == 'srgb':
                switch = 'hsl'
            elif mode == 'hsl':
                switch = 'hwb'
            else:
                switch = 'srgb'
            self.template_vars['color_value'] = self.color.to_string()
            self.template_vars['color_switch'] = switch
            self.get_color_info()

        mdpopups.show_popup(
            self.view,
            util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/color-picker.html'),
            css=util.ADD_CSS,
            wrapper_class="color-helper content",
            max_width=1024, max_height=(500 if hirespick or colornames else 725),
            on_navigate=self.handle_href,
            template_vars=self.template_vars
        )

    def handle_href(self, href):
        """Handle HREF."""

        print(href)
        hires = None
        mode = self.mode
        colornames = False
        if href in ('hsl', 'srgb', 'hwb'):
            print('this-------')
            color = self.color.convert(href).to_string()
            mode = href
        elif href.startswith('insert'):
            color = href.split(':')[1]
        elif href.startswith('hirespick'):
            hires = href.split(':')[1]
            color = self.color.to_string()
        elif href == "colornames":
            color = self.color.to_string()
            colornames = True
        elif href == 'edit':
            color = self.color.to_string()
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
                    "color": color,
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
                    "color": color,
                    "mode": mode, "hirespick": hires, "colornames": colornames,
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )


class ColorHelperPickerPanel(sublime_plugin.WindowCommand):
    """Open color picker with color from panel."""

    def run(
        self, color="#ffffffff", allowed_colors=util.ALL,
        use_hex_argb=None, compress_hex=False,
        on_done=None, on_cancel=None, space_separator_syntax=None,
        **kwargs
    ):
        """Run command."""

        self.on_done = on_done
        self.on_cancel = on_cancel
        # self.compress_hex = compress_hex
        # self.use_hex_argb = use_hex_argb
        # self.allowed_colors = allowed_colors
        # self.space_separator_syntax = space_separator_syntax
        self.color = colorcss(color)
        view = self.window.show_input_panel(
            'Color', self.color.to_string(), self.handle_value, None, None
        )
        view.sel().clear()
        view.sel().add(sublime.Region(0, view.size()))

    def handle_value(self, value):
        """Open color picker."""

        value = value.strip()
        try:
            color = colorcss(value)
        except Exception:
            color = None
        if color is None:
            color = colorcss("#ffffffff")
        view = self.window.active_view()
        if view is not None:
            view.settings().set('color_helper.no_auto', True)
            view.run_command(
                'color_helper_picker',
                {
                    "color": color.to_string(),
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )
