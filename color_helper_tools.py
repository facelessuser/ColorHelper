import sublime
import sublime_plugin
from coloraide.css import colorcss
import mdpopups
from .multiconf import get as qualify_settings
from . import color_helper_util as util
import copy
import functools
# import re

PREVIEW_IMG = '''\
<p>{}{}</p>
<p>{}</p>
'''

# RE_MIX = re.compile(r'^(.*?)(?:\s+\+\s+(.*?)([0-9]+(?:\.[0-9]+)?)?)?$' )


class _ColorInputHandler(sublime_plugin.TextInputHandler):
    def __init__(self, view, on_cancel=None, **kwargs):
        """Initialize."""

        self.view = view
        self.on_cancel = on_cancel

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
            border_color = colorcss(mdpopups.scope2style(view, '')['background']).convert("hsl")
            border_color.lightness = border_color.lightness + (20 if border_color.luminance() < 0.5 else 20)
        self.default_border = border_color.convert("srgb").to_string(hex_code=True, alpha=True)
        self.out_of_gamut_border = colorcss("red").to_string(hex_code=True, alpha=True)
        self.out_of_gamut = colorcss("rgb(0 0 0 / 0)").to_string(hex_code=True, alpha=True)
        self.set_sizes()

    def cancel(self):
        """On cancel."""

        if self.on_cancel is not None:
            call = self.on_cancel.get('command', 'color_helper')
            args = self.on_cancel.get('args', {})
            self.view.run_command(call, args)

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

        check_size = int((height - 4) / 8)
        if check_size < 2:
            check_size = 2
        return check_size


class ColorInputHandler(_ColorInputHandler):
    def __init__(self, view, initial=None, **kwargs):
        """Initialize."""

        self.color = initial
        super().__init__(view, **kwargs)

    def placeholder(self):
        """Placeholder."""

        return "Color"

    def initial_text(self):
        """Initial text."""

        if self.color is not None:
            return self.color
        elif len(self.view.sel()) == 1:
            return self.view.substr(self.view.sel()[0])

    def preview(self, color):
        """Preview."""

        try:
            color = colorcss(color)
            if color is None:
                return ""

            srgb = color.convert("srgb")
            preview_border = self.default_border
            message = ""
            if not srgb.in_gamut():
                srgb.fit_gamut("srgb")
                message = '<br><em style="font-size: 0.9em;">* color is out of gamut and was adjusted for preview</em>'
            preview = srgb.to_string(hex_code=True, alpha=False)
            preview_alpha = srgb.to_string(hex_code=True, alpha=True)
            preview_border = self.default_border

            height = self.height * 4
            width = self.width * 4
            check_size = self.check_size(height)

            html = PREVIEW_IMG.format(
                mdpopups.color_box(
                    [
                        preview,
                        preview_alpha
                    ], preview_border, border_size=1, height=height, width=width, check_size=check_size
                ),
                message,
                color.to_string()
            )

            return sublime.Html(html)
        except Exception as e:
            import traceback
            return str(traceback.format_exc())

    def validate(self, color):
        """Validate."""

        try:
            color = colorcss(color)
            return color is not None
        except Exception:
            return False


class ColorHelperEditCommand(sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, view, color, on_done=None, **kwargs
    ):
        """Run command."""

        if on_done is not None:
            call = on_done.get('command', 'color_helper')
            args = copy.deepcopy(on_done.get('args', {}))
            args["color"] = color
            self.view.run_command(call, args)

    def input(self, kwargs):
        """Input."""

        return ColorInputHandler(self.view, **kwargs)
