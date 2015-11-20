"""Popup color picker."""
import mdpopups
import sublime
import sublime_plugin
from ColorHelper.lib import csscolors
import ColorHelper.color_helper_util as util
import copy

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

WEB_COLOR = '''<span class="constant numeric">%s</span><br>'''
HEX_COLOR = '''<span class="support type">%s</span><br>'''
RGB_COLOR = '''<span class="keyword">rgb</span>(<span class="constant numeric">%d, %d, %d</span>)<br>'''
RGBA_COLOR = '''<span class="keyword">rgba</span>(<span class="constant numeric">%d, %d, %d, %s</span>)<br>'''
HSL_COLOR = '''<span class="keyword">hsl</span>(<span class="constant numeric">%s, %s%%, %s%%</span>)<br>'''
HSLA_COLOR = '''<span class="keyword">hsla</span>(<span class="constant numeric">%s, %s%%, %s%%, %s</span>)<br>'''

SPACER = '#00000000'
OUTER_BORDER = '#fefefeff'
INNER_BORDER = '#333333ff'


class ColorHelperPickerCommand(sublime_plugin.TextCommand):
    """Experimental color picker."""

    def get_color_map(self, text):
        """Get color wheel."""

        global color_map
        global color_map_size

        if color_map is None or self.graphic_size != color_map_size:
            color_map_size = self.graphic_size
            padding = (self.width * 9)
            decrement = True
            html_colors = []
            for row in color_map_data:
                html_colors.append('<span class="color-wheel">')
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
            '<span class="color-wheel current-color">%s</span>\n\n' % (
                mdpopups.color_box(
                    [SPACER], border_size=0,
                    height=self.height, width=(self.width * 6), check_size=2, alpha=True
                ) +
                mdpopups.color_box(
                    [self.color], OUTER_BORDER, INNER_BORDER,
                    border_size=2, height=self.height, width=self.width * 13, check_size=2
                )
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
        text.append('<span class="color-wheel"><a href="hirespick:%s">%s:</a>' % (color_filter, label))
        temp = []
        count = 12
        while count:
            getattr(rgba1, color_filter)(minimum)
            temp.append(
                '[%s](%s)' % (
                    mdpopups.color_box(
                        [rgba1.get_rgba()], OUTER_BORDER, INNER_BORDER,
                        border_size=2, height=self.height, width=self.width, check_size=2
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
            text.append(
                '[%s](%s)' % (
                    mdpopups.color_box(
                        [rgba2.get_rgba()], OUTER_BORDER, INNER_BORDER,
                        border_size=2, height=self.height, width=self.width, check_size=2
                    ),
                    rgba2.get_rgba()
                )
            )
            count -= 1
        text.append('</span>\n\n')

    def get_color_info(self, text):
        """Get color info."""

        rgba = util.RGBA(self.color)

        text.append('<div class="highlight"><pre>')
        if self.web_color:
            text.append(WEB_COLOR % self.web_color)
        text.append(HEX_COLOR % self.color[:-2].lower())
        text.append(RGB_COLOR % (rgba.r, rgba.g, rgba.b))
        text.append(RGBA_COLOR % (rgba.r, rgba.g, rgba.b, self.alpha))
        h, l, s = rgba.tohls()
        text.append(
            HSL_COLOR % (util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0))
        )
        text.append(
            HSLA_COLOR % (
                util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0),
                self.alpha
            )
        )
        text.append('</pre></div>')

    def set_sizes(self):
        """Get sizes."""

        settings = sublime.load_settings('color_helper.sublime-settings')
        self.graphic_size = settings.get('graphic_size', "medium")
        sizes = {
            "small": (10, 14, 16),
            "medium": (14, 18, 20),
            "large": (18, 22, 24)
        }
        self.height, self.width, self.height_big = sizes.get(
            self.graphic_size,
            sizes["medium"]
        )

    def run(self, edit, color='#ffffff', hsl=False, hirespick=None, on_done=None, on_cancel=None):
        """Run command."""

        self.on_done = on_done
        self.on_cancel = on_cancel
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
        if hirespick:
            text.append('[cancel](%s){: .color-helper .small} ' % self.color)
            text.append('\n\n## %s\n\n' % hirespick)
            self.get_hires_color_channel(text, hirespick)
        else:
            text.append('[cancel](cancel){: .color-helper .small} ')
            text.append('[select](insert){: .color-helper .small} ')
            text.append('[enter new color](edit){: .color-helper .small}\n\n')
            self.get_color_map(text)
            self.get_current_color(text)
            text.append('\n\n---\n\n')
            if hsl:
                self.get_channel(text, 'H', -15, 15, 'hue')
                self.get_channel(text, 'S', 0.975, 1.025, 'saturation')
                self.get_channel(text, 'L', 0.975, 1.025, 'luminance')
            else:
                self.get_channel(text, 'R', 0.95, 1.05, 'red')
                self.get_channel(text, 'G', 0.95, 1.05, 'green')
                self.get_channel(text, 'B', 0.95, 1.05, 'blue')
            self.get_channel(text, 'A', 0.95, 1.05, 'alpha')
            text.append(
                '[switch to %s](%s){: .color-helper .small}\n' % (
                    'rgb' if self.hsl else 'hsl', 'rgb' if self.hsl else 'hsl'
                )
            )
            text.append('\n\n---\n\n')
            self.get_color_info(text)

        mdpopups.show_popup(
            self.view, ''.join(text), css=util.ADD_CSS,
            max_width=600, max_height=(500 if hirespick else 725),
            on_navigate=self.handle_href
        )

    def handle_href(self, href):
        """Handle href."""

        hires = None
        if href in ('hsl', 'rgb'):
            hsl = href == 'hsl'
            color = self.color
        elif href == 'insert':
            hsl = self.hsl
            color = self.color
        elif href.startswith('hirespick'):
            hires = href.split(':')[1]
            color = self.color
            hsl = self.hsl
        elif href == 'edit':
            color = self.color
            hsl = self.hsl
        else:
            hsl = self.hsl
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
                {"color": color, "on_done": self.on_done, "on_cancel": self.on_cancel}
            )
        elif href == 'insert':
            mdpopups.hide_popup(self.view)
            if self.on_done is not None:
                call = self.on_done.get('command', 'color_helper')
                args = copy.deepcopy(self.on_done.get('args', {}))
                args['color'] = color
                self.view.run_command(call, args)
        else:
            self.view.run_command(
                'color_helper_picker',
                {"color": color, "hsl": hsl, "hirespick": hires, "on_done": self.on_done, "on_cancel": self.on_cancel}
            )


class ColorHelperPickerPanel(sublime_plugin.WindowCommand):
    """Open color picker with color from panel."""

    def run(self, color="#ffffffff", on_done=None, on_cancel=None):
        """Run command."""

        self.on_done = on_done
        self.on_cancel = on_cancel
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
                {"color": value, "on_done": self.on_done, "on_cancel": self.on_cancel}
            )
