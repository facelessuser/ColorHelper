"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
import mdpopups
from mdpopups import colorbox
from coloraide import Color
from coloraide import util as cutil
from coloraide.css.colors import css_names
from . import color_helper_util as util
from .color_helper_mixin import _ColorMixin
from .color_helper_util import DEFAULT, COLOR_FULL_PREC, HEX, HEX_NA
import copy

color_map = None
color_map_size = False
line_height = None
default_border = None
color_scale = None

BORDER_SIZE = 1


class ColorHelperPickerCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Experimental color picker."""

    def setup(self, color, mode, controls, on_done, on_cancel):
        """Setup properties for rendering."""

        self.on_done = on_done
        self.on_cancel = on_cancel
        self.template_vars = {}
        color = Color(color)
        self.setup_gamut_style()
        self.setup_image_border()
        self.setup_sizes()
        self.height_big = int(self.height + self.height / 4)
        self.setup_mode(color, mode)
        self.setup_controls(controls)
        self.color = color.convert(self.mode, fit=True)
        # Ensure hue is between 0 - 360.
        if self.color.space() != "srgb" and not self.color.is_nan("hue"):
            self.color.hue = self.color.hue % 360

    def setup_mode(self, color, mode):
        """Setup mode."""

        # Use the provided mode, if any, or use the mode of the color
        # If the color is not one of the supported spaces, use sRGB.
        if mode is None or mode not in ("srgb", "hsl", "hwb"):
            if color.space() in ("srgb", "hsl", "hwb"):
                mode = color.space()
            else:
                mode = "srgb"
        self.mode = mode

    def setup_controls(self, controls):
        """Setup controls."""

        if controls is None or controls not in ('box', 'sliders'):
            controls = 'box'
        self.controls = controls

    def get_color_map_square(self):
        """Get a square variant of the color map."""

        global color_map
        global color_map_size
        global line_height
        global default_border
        global color_scale

        hue, saturation, lightness = cutil.no_nan(self.color.convert('hsl').coords())
        alpha = cutil.no_nan(self.color.alpha)

        r_sat = cutil.round_half_up(saturation / 100, 1) * 100
        r_lit = cutil.round_half_up(lightness / 100, 1) * 100

        # Only update if the last time we rendered we changed
        # something that would require a new render.
        if (True):
            color_map_size = self.graphic_size
            color_scale = self.graphic_scale

            line_height = self.line_height
            default_border = self.default_border

            html_colors = []

            # Generate the colors with each row being darker than the last.
            # Each column will progress through hues.
            color = Color("hsl(0 100% {}% / {})".format(lightness, alpha), filters=util.SRGB_SPACES)
            if color.is_nan("hue"):
                color.hue = 0.0
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                html_colors.append([])
                for x in range(0, 17):
                    this_hue = False
                    this_sat = color.saturation == r_sat
                    border_color = self.default_border
                    if this_sat:
                        this_hue = abs(color.hue - hue) < 11.21875
                        if this_hue:
                            lum = color.luminance()
                            border_color = '#ffffff' if lum < 0.5 else '#000000'
                    value = color.convert("srgb").to_string(**HEX_NA)
                    kwargs = {
                        "border_size": BORDER_SIZE, "height": self.height, "width": self.width,
                        "check_size": check_size
                    }

                    if this_hue and this_sat:
                        border_map = colorbox.TOP | colorbox.LEFT | colorbox.BOTTOM | colorbox.RIGHT
                    elif y == 0 and x == 0:
                        border_map = colorbox.TOP | colorbox.LEFT
                    elif y == 0 and x == 16:
                        border_map = colorbox.TOP | colorbox.RIGHT
                    elif y == 0:
                        border_map = colorbox.TOP
                    elif y == 10 and x == 0:
                        border_map = colorbox.BOTTOM | colorbox.LEFT
                    elif y == 10 and x == 16:
                        border_map = colorbox.BOTTOM | colorbox.RIGHT
                    elif y == 10:
                        border_map = colorbox.BOTTOM
                    elif x == 0:
                        border_map = colorbox.LEFT
                    elif x == 16:
                        border_map = colorbox.RIGHT
                    else:
                        border_map = 0
                    kwargs["border_map"] = border_map

                    html_colors[-1].append(
                        '<a href="{}">{}</a>'.format(
                            color.to_string(**COLOR_FULL_PREC),
                            mdpopups.color_box(
                                [value], border_color,
                                **kwargs
                            )
                        )
                    )
                    color.hue = color.hue + 22.4375
                color.hue = 0.0
                color.saturation = color.saturation - 10

            # Generate a grayscale bar.
            color = Color('hsl({} {}% 100% / {})'.format(hue, saturation, alpha), filters=util.SRGB_SPACES)
            if color.is_nan("hue"):
                color.hue = 0.0
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                value = color.convert("srgb").to_string(**HEX_NA)
                kwargs = {
                    "border_size": BORDER_SIZE, "height": self.height, "width": self.width, "check_size": check_size
                }

                this_lit = color.lightness == r_lit
                border_color = self.default_border
                if this_lit:
                    lum = color.luminance()
                    border_color = '#ffffff' if lum < 0.5 else '#000000'

                if this_lit:
                    border_map = colorbox.TOP | colorbox.LEFT | colorbox.BOTTOM | colorbox.RIGHT
                elif y == 0:
                    border_map = colorbox.TOP | colorbox.LEFT | colorbox.RIGHT
                elif y == 10:
                    border_map = colorbox.BOTTOM | colorbox.LEFT | colorbox.RIGHT
                else:
                    border_map = colorbox.LEFT | colorbox.RIGHT
                kwargs["border_map"] = border_map

                html_colors[y].append(
                    '<a href="{}">{}</a>'.format(
                        color.to_string(**COLOR_FULL_PREC),
                        mdpopups.color_box(
                            [value], border_color,
                            **kwargs
                        )
                    )
                )
                color.lightness = color.lightness - 10

            color_map = (
                ''.join(['<span>{}</span><br>'.format(''.join([y1 for y1 in x1])) for x1 in html_colors])
            )
        self.template_vars['color_picker'] = color_map

    def get_current_color(self):
        """Get current color."""

        # Show a preview of the current color.
        check_size = self.check_size(self.height * 2)
        preview = self.color.convert("srgb")
        html = (
            '<span class="current-color">{}</span>'.format(
                mdpopups.color_box(
                    [preview.to_string(**HEX_NA), preview.to_string(**HEX)],
                    self.default_border,
                    border_size=BORDER_SIZE, height=self.height * 3, width=self.width * 3,
                    check_size=check_size
                )
            )
        )
        self.template_vars['current_color'] = html

    def get_css_color_names(self):
        """Get CSS color names."""

        check_size = self.check_size(self.height)
        html = []
        for name in sorted(css_names.name2hex_map):
            color = Color(name, filters=util.SRGB_SPACES)

            html.append(
                '[{}]({}) {}<br>'.format(
                    mdpopups.color_box(
                        [color.to_string(**HEX)], self.default_border,
                        border_size=BORDER_SIZE, height=self.height, width=self.height * 8,
                        check_size=check_size
                    ),
                    color.to_string(**COLOR_FULL_PREC),
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
            "hue": (0, 359),
            "saturation": (0, 100),
            "lightness": (0, 100),
            "whiteness": (0, 100),
            "blackness": (0, 100)
        }

        options = HEX_NA if color_filter != 'alpha' else HEX
        minimum, maximum = ranges[color_filter]
        check_size = self.check_size(self.height)
        html = []
        color = self.color.clone()
        current = color.get(color_filter)
        if color_filter in ('red', 'green', 'blue'):
            estimate = int(cutil.fmt_float(current * 255, 0))
            current = '{}'.format(cutil.fmt_float(current * 255, 5))
        elif color_filter in ('alpha',):
            estimate = int(cutil.fmt_float(current * 100, 0))
            current = '{}%'.format(cutil.fmt_float(current * 100, 5))
        elif color_filter in ('whiteness', 'blackness', 'saturation', 'lightness'):
            estimate = int(cutil.fmt_float(current, 0))
            current = '{}%'.format(cutil.fmt_float(current, 5))
        elif color_filter in ('hue',):
            estimate = int(cutil.fmt_float(current, 0))
            current = '{}\xb0'.format(cutil.fmt_float(current, 5))

        for x in range(minimum, maximum + 1):
            if x == estimate:
                label = '{} <'
            else:
                label = '{}'
            if color_filter in ('red', 'green', 'blue'):
                color.set(color_filter, x / 255.0)
                label = label.format(str(x))
            elif color_filter == 'alpha':
                color.alpha = x / 100.0
                label = label.format("{:d}%".format(x))
            elif color_filter == 'hue':
                color.hue = x
                label = label.format("{:d}\xb0".format(x))
            elif color_filter in ('saturation', 'lightness', 'whiteness', 'blackness'):
                color.set(color_filter, x)
                label = label.format("{:d}%".format(x))

            html.append(
                '[{}]({}) {}<br>'.format(
                    mdpopups.color_box(
                        [color.convert("srgb").to_string(**options)], self.default_border,
                        border_size=BORDER_SIZE, height=self.height, width=self.height * 8,
                        check_size=check_size
                    ),
                    color.to_string(**COLOR_FULL_PREC),
                    label
                )
            )
        self.template_vars['hires_color'] = '{} ({})'.format(color_filter, current)
        self.template_vars['channel_hires'] = ''.join(html)

    def get_channel(self, channel, label, color_filter):
        """Get color channel."""

        html = []
        html.append(
            '<span class="channel"><a class="small button" href="__hirespick__:{}">{}:</a> '.format(
                color_filter, label
            )
        )
        temp = []
        count = 10
        check_size = self.check_size(self.height)
        clone = self.color.clone()
        options = HEX_NA if color_filter != 'alpha' else HEX

        coord = cutil.no_nan(getattr(clone, color_filter))
        if color_filter in ('red', 'green', 'blue', 'alpha'):
            rounded = cutil.round_half_up(coord, 2)
            setattr(clone, color_filter, rounded)
            step = 0.01
        elif color_filter in ('lightness', 'saturation', 'whiteness', 'blackness'):
            rounded = cutil.round_half_up(coord, 0)
            setattr(clone, color_filter, rounded)
            step = 1
        else:
            rounded = cutil.round_half_up(coord / 359, 2) * 359
            setattr(clone, color_filter, rounded)
            step = 3.59

        first = True
        while count:
            coord = cutil.no_nan(getattr(clone, color_filter)) - step
            setattr(clone, color_filter, coord)

            if not clone.in_gamut():
                temp.append(self.get_spacer(width=count))
                break
            elif color_filter == "alpha" and (coord < 0 or coord > 1.0):
                temp.append(self.get_spacer(width=count))
                break
            elif self.mode in ("hsl", "hwb") and color_filter == "hue" and (coord < 0 or coord > 359):
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
                    '<a href="{}" title="{}">{}</a>'.format(
                        clone.to_string(**COLOR_FULL_PREC),
                        clone.to_string(),
                        mdpopups.color_box(
                            [clone.convert("srgb").to_string(**options)], self.default_border,
                            **kwargs
                        )
                    )
                )
            count -= 1
        html += reversed(temp)
        html.append(
            '<a href="{}" title="{}">{}</a>'.format(
                self.color.to_string(**COLOR_FULL_PREC),
                clone.to_string(),
                mdpopups.color_box(
                    [self.color.convert("srgb").to_string(**options)], self.default_border,
                    border_size=BORDER_SIZE, height=self.height_big, width=self.width, check_size=check_size
                )
            )
        )
        first = True
        count = 10

        clone.update(self.color)
        setattr(clone, color_filter, rounded)
        while count:
            coord = cutil.no_nan(getattr(clone, color_filter)) + step
            setattr(clone, color_filter, coord)

            if not clone.in_gamut():
                html.append(self.get_spacer(width=count))
                break
            elif color_filter == "alpha" and (coord < 0 or coord > 1.0):
                html.append(self.get_spacer(width=count))
                break
            elif self.mode in ("hsl", "hwb") and color_filter == "hue" and (coord < 0 or coord > 359):
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
                    '<a href="{}" title="{}">{}</a>'.format(
                        clone.to_string(**COLOR_FULL_PREC),
                        clone.to_string(),
                        mdpopups.color_box(
                            [clone.convert("srgb").to_string(**options)], self.default_border,
                            **kwargs
                        )
                    )
                )
            count -= 1
        html.append('</span><br>')
        self.template_vars[channel] = ''.join(html)

    def show_tools(self):
        """Show tools."""

        template_vars = {}
        template_vars["back_target"] = self.color.to_string(**COLOR_FULL_PREC)
        template_vars['tools'] = [
            ('Edit and Mix', '__tool__:__edit__'),
            ('Contrast', '__tool__:__contrast__'),
            ('Sublime ColorMod', '__tool__:__colormod__')
        ]

        mdpopups.show_popup(
            self.view,
            util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/tools.html.j2'),
            wrapper_class="color-helper content",
            css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
            on_navigate=self.handle_href,
            flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
            template_vars=template_vars
        )

    def handle_href(self, href):
        """Handle HREF."""

        hires = None
        colornames = False
        mode = self.mode
        tool = None
        controls = self.controls
        if href.startswith('__space__'):
            # If we received a color space switch to that picker.
            space = href.split(':')[1]
            color = self.color.convert(space).to_string(**COLOR_FULL_PREC)
            mode = space
        elif href.startswith('__controls__'):
            color = self.color.to_string(**COLOR_FULL_PREC)
            controls = href.split(':')[1]
        elif href.startswith('__insert__'):
            # We will need to call the insert dialog
            color = href.split(':')[1]
        elif href.startswith('__hirespick__'):
            # We need to open a high resolution channel picker
            hires = href.split(':')[1]
            color = self.color.to_string(**COLOR_FULL_PREC)
        elif href.startswith('__tools__'):
            color = self.color.to_string(**COLOR_FULL_PREC)
        elif href.startswith('__tool__'):
            tool = href.split(':')[1]
            color = self.color.to_string(**DEFAULT)
        elif href == "__colornames__":
            # We need to open the color name picker
            color = self.color.to_string(**COLOR_FULL_PREC)
            colornames = True
        else:
            # Process we need to update the current color
            color = href
        if href == '__cancel__':
            # Close color picker and call the callback if one was provided
            mdpopups.hide_popup(self.view)
            if self.on_cancel is not None:
                call = self.on_cancel.get('command', 'color_helper')
                args = self.on_cancel.get('args', {})
                self.view.run_command(call, args)
        elif href == '__tools__':
            self.show_tools()
        elif href.startswith('__tool__'):
            # Edit color in edit panel
            mdpopups.hide_popup(self.view)

            # Provide callback info for the color picker.
            on_done = {
                "command": "color_helper_picker",
                "args": {
                    "mode": self.mode,
                    "controls": self.controls
                }
            }

            # On edit cancel, call the color picker with the current color.
            on_cancel = {
                "command": "color_helper_picker",
                "args": {
                    "mode": self.mode,
                    "controls": self.controls,
                    "color": self.color.to_string(**COLOR_FULL_PREC)
                }
            }

            if tool == '__contrast__':
                cmd = 'color_helper_contrast_ratio'
            elif tool == "__colormod__":
                cmd = 'color_helper_sublime_color_mod'
            else:
                cmd = 'color_helper_edit'

            # Call the edit input panel
            self.view.run_command(
                cmd,
                {
                    "initial": Color(color, filters=util.SRGB_SPACES).to_string(**DEFAULT),
                    "on_done": on_done, "on_cancel": on_cancel
                }
            )

        elif href.startswith('__insert__'):
            # Call back to ColorHelper to insert the color.
            mdpopups.hide_popup(self.view)
            if self.on_done is None:
                on_done = {
                    'command': 'color_helper',
                    'args': {'mode': "result", "result_type": "__color_picker__"}
                }
            else:
                on_done = self.on_done
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color
            self.view.run_command(call, args)
        else:
            # Call color picker with the provided color.
            self.view.run_command(
                'color_helper_picker',
                {
                    "color": color,
                    "mode": mode, "hirespick": hires, "colornames": colornames, "controls": controls,
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )

    def run(
        self, edit, color='#ffffff', mode=None, hirespick=None, colornames=False, controls="box",
        on_done=None, on_cancel=None, **kwargs
    ):
        """Run command."""

        # Setup
        self.setup(color, mode, controls, on_done, on_cancel)

        # Show the appropriate dialog
        if colornames:
            template = 'Packages/ColorHelper/panels/color-picker-names.html.j2'
            # Show color name picker
            self.template_vars['color_names'] = True
            self.template_vars['cancel'] = self.color.to_string(**COLOR_FULL_PREC)
            self.get_css_color_names()
        elif hirespick:
            template = 'Packages/ColorHelper/panels/color-picker-channel.html.j2'
            # Show high resolution channel picker
            self.template_vars['hires'] = True
            self.template_vars['cancel'] = self.color.to_string(**COLOR_FULL_PREC)
            self.get_hires_color_channel(hirespick)
        else:
            template = 'Packages/ColorHelper/panels/color-picker.html.j2'
            # Show the normal color picker of the specified space
            self.template_vars['picker'] = True
            self.template_vars['cancel'] = '__cancel__'
            if self.controls == "box":
                self.get_color_map_square()
            self.get_current_color()
            if self.controls == "sliders":
                if self.mode == "hsl":
                    self.get_channel('channel_1', 'H', 'hue')
                    self.get_channel('channel_2', 'S', 'saturation')
                    self.get_channel('channel_3', 'L', 'lightness')
                elif self.mode == "hwb":
                    self.get_channel('channel_1', 'H', 'hue')
                    self.get_channel('channel_2', 'W', 'whiteness')
                    self.get_channel('channel_3', 'B', 'blackness')
                else:
                    self.get_channel('channel_1', 'R', 'red')
                    self.get_channel('channel_2', 'G', 'green')
                    self.get_channel('channel_3', 'B', 'blue')
                self.get_channel('channel_alpha', 'A', 'alpha')

            self.template_vars['mode'] = self.mode
            self.template_vars['box_control'] = self.controls == 'box'
            self.template_vars['color_full'] = self.color.to_string(**COLOR_FULL_PREC)
            self.template_vars['color_display'] = "`#!color-helper {}`".format(self.color.to_string(**DEFAULT))
            self.template_vars['color_value'] = self.color.to_string(**DEFAULT)

        # Display picker
        mdpopups.show_popup(
            self.view,
            util.FRONTMATTER + sublime.load_resource(template),
            css=util.ADD_CSS,
            wrapper_class="color-helper content",
            max_width=1024, max_height=(500 if hirespick or colornames else 725),
            on_navigate=self.handle_href,
            template_vars=self.template_vars
        )
