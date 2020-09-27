"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
import mdpopups
from mdpopups import colorbox
from coloraide.css import Color
from coloraide.css.colors import css_names
from . import color_helper_util as util
from .color_helper_mixin import _ColorMixin
from .color_helper_util import GENERIC, HEX, HEX_NA
import copy

color_map = None
color_map_size = False
line_height = None
default_border = None
color_scale = None
last_saturation = None

BORDER_SIZE = 1


class ColorHelperPickerCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Experimental color picker."""

    def setup(self, color, mode, on_done, on_cancel):
        """Setup properties for rendering."""

        self.on_done = on_done
        self.on_cancel = on_cancel
        self.template_vars = {}
        color = Color(color)
        self.setup_image_border()
        self.setup_gamut_style()
        self.setup_sizes()
        self.height_big = int(self.height + self.height / 4)
        self.setup_mode(color, mode)
        self.color = color.convert(self.mode, fit=self.preferred_gamut_mapping)

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

    def get_color_map_square(self):
        """Get a square variant of the color map."""

        global color_map
        global color_map_size
        global line_height
        global default_border
        global color_scale
        global last_saturation

        s = self.color.convert("hsl").saturation

        # Only update if the last time we rendered we changed
        # something that would require a new render.
        if (
            color_map is None or
            s != last_saturation or
            self.graphic_size != color_map_size or
            self.graphic_scale != color_scale or
            self.line_height != line_height or
            self.default_border != default_border
        ):
            color_map_size = self.graphic_size
            color_scale = self.graphic_scale

            line_height = self.line_height
            default_border = self.default_border

            html_colors = []

            # Generate the colors with each row being dark than the last.
            # Each column will progress through hues.
            color = Color("hsl(0 {}% 90%)".format(s), filters=util.SRGB_SPACES)
            hfac = 24.0
            lfac = 8.0
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                html_colors.append([self.get_spacer(width=5)])
                for x in range(0, 15):
                    value = color.convert("srgb").to_string(**HEX)
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
                            color.to_string(**GENERIC),
                            mdpopups.color_box(
                                [value], self.default_border,
                                **kwargs
                            )
                        )
                    )
                    color.hue = color.hue + hfac
                color.hue = 0.0
                color.lightness = color.lightness - lfac

            # Generate a grayscale bar.
            lfac = 10.0
            color = Color('hsl(0 0% 100%)', filters=util.SRGB_SPACES)
            check_size = self.check_size(self.height)
            for y in range(0, 11):
                value = color.convert("srgb").to_string(**HEX)
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
                        color.to_string(**GENERIC),
                        mdpopups.color_box(
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

        # Show a preview of the current color.
        check_size = self.check_size(self.height * 2)
        preview = self.color.convert("srgb")
        html = (
            '<span class="current-color">{}</span>'.format(
                self.get_spacer(width=5) +
                mdpopups.color_box(
                    [preview.to_string(**HEX_NA), preview.to_string(**HEX)],
                    self.default_border,
                    border_size=BORDER_SIZE, height=self.height * 2, width=self.width * 16,
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
                '[%s](%s) %s<br>' % (
                    mdpopups.color_box(
                        [color.to_string(**HEX)], self.default_border,
                        border_size=BORDER_SIZE, height=self.height, width=self.height * 8,
                        check_size=check_size
                    ),
                    color.to_string(**GENERIC),
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
        check_size = self.check_size(self.height)
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
                        [color.convert("srgb").to_string(**HEX)], self.default_border,
                        border_size=BORDER_SIZE, height=self.height, width=self.height * 8,
                        check_size=check_size
                    ),
                    color.to_string(**GENERIC),
                    label
                )
            )
        self.template_vars['channel_hires'] = ''.join(html)

    def get_channel(self, channel, label, minimum, maximum, color_filter):
        """Get color channel."""

        html = []
        html.append('<span class="channel"><a href="__hirespick__:%s">%s:</a>' % (color_filter, label))
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
                            [clone.convert("srgb").to_string(**HEX)], self.default_border,
                            **kwargs
                        ),
                        clone.to_string(**GENERIC)
                    )
                )
            clone.update(self.color)
            mn += minimum
            count -= 1
        html += reversed(temp)
        html.append(
            '[%s](%s)' % (
                mdpopups.color_box(
                    [self.color.convert("srgb").to_string(**HEX)], self.default_border,
                    border_size=BORDER_SIZE, height=self.height_big, width=self.width, check_size=check_size
                ),
                self.color.to_string(**GENERIC)
            )
        )
        first = True
        count = 12
        mx = maximum

        clone.update(self.color)
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
                            [clone.convert("srgb").to_string(**HEX)], self.default_border,
                            **kwargs
                        ),
                        clone.to_string(**GENERIC)
                    )
                )
            clone.update(self.color)
            mx += maximum
            count -= 1
        html.append('</span><br>')
        self.template_vars[channel] = ''.join(html)

    def handle_href(self, href):
        """Handle HREF."""

        hires = None
        colornames = False
        mode = self.mode
        edit_style = None
        if href.startswith('__space__'):
            # If we received a color space switch to that picker.
            space = href.split(':')[1]
            color = self.color.convert(space).to_string(**GENERIC)
            mode = space
        elif href.startswith('__insert__'):
            # We will need to call the insert dialog
            color = href.split(':')[1]
        elif href.startswith('__hirespick__'):
            # We need to open a high resolution channel picker
            hires = href.split(':')[1]
            color = self.color.to_string(**GENERIC)
        elif href == "__colornames__":
            # We need to open the color name picker
            color = self.color.to_string(**GENERIC)
            colornames = True
        elif href.startswith(('__edit__', '__contrast__')):
            # We want to edit the color
            color = self.color.to_string(**GENERIC)
            if href.startswith('__edit__'):
                edit_style = href.split(":")[1]
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
        elif href.startswith(('__edit__', '__contrast__')):
            # Edit color in edit panel
            mdpopups.hide_popup(self.view)

            # Provide callback info for the color picker.
            on_done = {
                "command": "color_helper_picker",
                "args": {
                    "mode": self.mode
                }
            }

            # On edit cancel, call the color picker with the current color.
            on_cancel = {
                "command": "color_helper_picker",
                "args": {
                    "mode": self.mode,
                    "color": self.color.to_string(**GENERIC)
                }
            }

            if href.startswith('__contrast__'):
                cmd = 'color_helper_contrast_ratio'
            elif edit_style == "st-colormod":
                cmd = 'color_helper_sublime_color_mod'
            else:
                cmd = 'color_helper_edit'

            # Call the edit input panel
            self.view.run_command(
                cmd,
                {
                    "initial": Color(color, filters=util.SRGB_SPACES).to_string(),
                    "on_done": on_done, "on_cancel": on_cancel
                }
            )

        elif href.startswith('__insert__'):
            # Call back to ColorHelper to insert the color.
            mdpopups.hide_popup(self.view)
            if self.on_done is None:
                on_done = {'command': 'color_helper', 'args': {'mode': "color_picker_result"}}
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
                    "mode": mode, "hirespick": hires, "colornames": colornames,
                    "on_done": self.on_done, "on_cancel": self.on_cancel
                }
            )

    def run(
        self, edit, color='#ffffff', mode=None, hirespick=None, colornames=False,
        on_done=None, on_cancel=None, **kwargs
    ):
        """Run command."""

        # Setup
        self.setup(color, mode, on_done, on_cancel)

        # Show the appropriate dialog
        if colornames:
            # Show color name picker
            self.template_vars['color_names'] = True
            self.template_vars['cancel'] = self.color
            self.get_css_color_names()
        elif hirespick:
            # Show high resolution channel picker
            self.template_vars['hires'] = True
            self.template_vars['cancel'] = self.color
            self.template_vars['hires_color'] = hirespick
            self.get_hires_color_channel(hirespick)
        else:
            s = sublime.load_settings('color_helper.sublime-settings')
            rules = util.get_rules(self.view)
            if rules is None:
                rules = s.get("generic", {})
            edit_style = rules.get("edit_mode", "default")
            if edit_style not in ("default", "st-colormod"):
                edit_style = "default"

            # Show the normal color picker of the specified space
            self.template_vars['edit_mode'] = edit_style
            self.template_vars['picker'] = True
            self.template_vars['cancel'] = '__cancel__'
            self.get_color_map_square()
            self.get_current_color()
            if self.mode == "hsl":
                self.get_channel('channel_1', 'H', -5, 5, 'hue')
                self.get_channel('channel_2', 'S', -1, 1, 'saturation')
                self.get_channel('channel_3', 'L', -1, 1, 'lightness')
            elif self.mode == "hwb":
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

        # Display picker
        mdpopups.show_popup(
            self.view,
            util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/color-picker.html'),
            css=util.ADD_CSS,
            wrapper_class="color-helper content",
            max_width=1024, max_height=(500 if hirespick or colornames else 725),
            on_navigate=self.handle_href,
            template_vars=self.template_vars
        )
