import sublime
import sublime_plugin
from coloraide.css import colorcss
import mdpopups
from .multiconf import get as qualify_settings
from . import color_helper_util as util
from .color_helper_mixin import _ColorBoxMixin
import copy
import functools
# import re

PREVIEW_IMG = '''\
<p>{}{}</p>
<p>{}</p>
'''

# RE_MIX = re.compile(r'^(.*?)(?:\s+\+\s+(.*?)([0-9]+(?:\.[0-9]+)?)?)?$' )


class _ColorInputHandler(_ColorBoxMixin, sublime_plugin.TextInputHandler):
    """Color input handler base class."""

    def __init__(self, view, on_cancel=None, **kwargs):
        """Initialize."""

        self.view = view
        self.on_cancel = on_cancel
        self.setup_image_border()
        self.setup_sizes()

    def cancel(self):
        """On cancel."""

        if self.on_cancel is not None:
            call = self.on_cancel.get('command', 'color_helper')
            args = self.on_cancel.get('args', {})
            self.view.run_command(call, args)


class ColorInputHandler(_ColorInputHandler):
    """Handle color inputs."""

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
            check_size = self.check_size(height, scale=8)

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
