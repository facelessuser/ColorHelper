"""ColorMod tool."""
import sublime
import sublime_plugin
from .lib.coloraide import Color
import mdpopups
from . import ch_util as util
from . import ch_tools as tools
from .ch_mixin import _ColorMixin
import copy


DEF_COLORMOD = """---
markdown_extensions:
- markdown.extensions.attr_list
- markdown.extensions.def_list
- pymdownx.betterem
...

{}

## Format

<code>color(color_syntax adjuster*)</code>

Also accepts normal CSS color syntax. Color functions can be nested.

## Instructions

Colors must be in the **sRGB**, **HSL**, or **HSB** color space.

Supported adjusters are <code>alpha()</code>, <code>a()</code>, <code>lightness()</code>, <code>l()</code>,<br>
<code>saturation()</code>, <code>s()</code>, <code>blend()</code>, and <code>blenda()</code>.

Please see [Sublime Text Documentation](https://www.sublimetext.com/docs/color_schemes.html#colors) for more info.
"""


class ColorHelperColorModInputHandler(tools._ColorInputHandler):
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

        self.color_mod_class = util.import_color("ColorHelper.custom.st_colormod.Color")
        if self.color is not None:
            return self.color
        elif len(self.view.sel()) == 1:
            self.setup_color_class()
            text = self.view.substr(self.view.sel()[0])
            if text:
                color = None
                if self.custom_color_class == self.color_mod_class:
                    # Try and handle a `color()` case if the file uses `color-mod`.
                    # Basically, if the file already supports `color-mod` input,
                    # then we want to return the text raw if it parses.
                    try:
                        color = self.color_mod_class(text, filters=util.SRGB_SPACES)
                    except Exception:
                        pass
                if color is None:
                    # Try to use the current file's input format and convert input
                    # to the default string output for the color.
                    try:
                        color = self.custom_color_class(text, filters=self.filters)
                    except Exception:
                        pass
                    if color is not None:
                        # convert to a `color-mod` instance.
                        return self.color_mod_class(color).to_string(**util.DEFAULT)
                else:
                    return text
        return ''

    def preview(self, text):
        """Preview."""

        style = self.get_html_style()

        try:
            color = self.color_mod_class(text.strip())
            if color is not None:
                srgb = Color(color).convert("srgb")
                preview_border = self.default_border
                message = ""
                if not srgb.in_gamut():
                    srgb.fit()
                    message = '<br><em style="font-size: 0.9em;">* preview out of gamut</em>'
                preview = srgb.to_string(**util.HEX_NA)
                preview_alpha = srgb.to_string(**util.HEX)
                preview_border = self.default_border
                temp = Color(preview_border)
                if temp.luminance() < 0.5:
                    second_border = temp.mix('white', 0.25, space="srgb").to_string(**util.HEX_NA)
                else:
                    second_border = temp.mix('black', 0.25, space="srgb").to_string(**util.HEX_NA)

                height = self.height * 3
                width = self.width * 3
                check_size = self.check_size(height, scale=8)

                html = tools.PREVIEW_IMG.format(
                    mdpopups.color_box(
                        [preview, preview_alpha],
                        preview_border, second_border,
                        border_size=1, height=height, width=width, check_size=check_size
                    ),
                    message,
                    color.to_string(**util.DEFAULT)
                )
            if html:
                return sublime.Html(style + html)
            else:
                return sublime.Html(mdpopups.md2html(self.view, DEF_COLORMOD.format(style)))
        except Exception:
            return sublime.Html(mdpopups.md2html(self.view, DEF_COLORMOD.format(style)))

    def validate(self, color):
        """Validate."""

        try:
            color = self.color_mod_class(color.strip())
            return color is not None
        except Exception:
            return False


class ColorHelperSublimeColorModCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, edit, color_helper_color_mod, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        text = color_helper_color_mod.strip()
        self.custom_color_class = util.import_color("ColorHelper.custom.st_colormod.Color")
        color = self.custom_color_class(text)

        if color is not None:
            if on_done is None:
                on_done = {
                    'command': 'color_helper',
                    'args': {'mode': "result", "insert_raw": text, "result_type": "__tool__:__colormod__"}
                }
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.COLOR_FULL_PREC)
            args['insert_raw'] = text
            self.view.run_command(call, args)

    def input(self, kwargs):  # noqa: A003
        """Input."""

        return ColorHelperColorModInputHandler(self.view, **kwargs)
