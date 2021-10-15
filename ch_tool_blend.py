"""Color edit tool."""
import sublime
import sublime_plugin
from .lib.coloraide import Color
import mdpopups
from .lib import colorbox
from . import ch_util as util
from .ch_mixin import _ColorMixin
import copy
from . import ch_tools as tools

DEF_EDIT = """---
markdown_extensions:
- markdown.extensions.attr_list
- markdown.extensions.def_list
- pymdownx.betterem
...

{}

## Format

<code>Source( + Backdrop)?( !blendmode)?( @colorspace)?</code>

## Instructions

Colors are blended in sRGB color space unless a different space is specified<br>
by <code>@colorspace</code>. Colors will be gamut mapped to the specified color space.<br>
Blend modes are designed for RGB-ish color spaces, even if the accepts other<br>
spaces.

If two colors are provided, joined with <code>+</code>, the colors will be blended.<br>
Default blend mode is <code>normal</code>, but can be changed with <code>!blendmode</code>.

Transparent backdrops will be <code>normal</code> blended with white.
"""


def parse_color(string, start=0, second=False):
    """
    Parse colors.

    The return of `more`:
    - `None`: there is no more colors to process
    - `True`: there are more colors to process
    - `False`: there are more colors to process, but we failed to find them.
    """

    length = len(string)
    more = None
    space = None
    blend_mode = 'normal'
    # First color
    color = Color.match(string, start=start, fullmatch=False)
    if color:
        start = color.end
        if color.end != length:
            more = True

            # Is the first color in the input or the second?
            if not second:
                # Plus sign indicating we have an additional color to mix
                m = tools.RE_PLUS.match(string, start)
                if m:
                    start = m.end(0)
                    more = start != length
                else:
                    m = tools.RE_MODE.match(string, start)
                    if m:
                        blend_mode = m.group(1)
                        start = m.end(0)

                    m = tools.RE_SPACE.match(string, start)
                    if m:
                        text = m.group(1).lower()
                        if text in color.color.CS_MAP:
                            space = text
                            start = m.end(0)
                    more = None if start == length else False
            else:
                m = tools.RE_MODE.match(string, start)
                if m:
                    blend_mode = m.group(1)
                    start = m.end(0)

                # Color space indicator
                m = tools.RE_SPACE.match(string, start)
                if m:
                    text = m.group(1).lower()
                    if text in color.color.CS_MAP:
                        space = text
                        start = m.end(0)
                more = None if start == length else False

    if color:
        color.end = start

    return color, more, space, blend_mode


def evaluate(string):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        second = None
        blend_mode = 'normal'
        space = None

        # Try to capture the color or the two colors to mix
        first, more, space, blend_mode = parse_color(color)
        if first and more is not None:
            if more is False:
                first = None
            else:
                second, more, space, blend_mode = parse_color(color, start=first.end, second=True)
                if not second or more is False:
                    first = None
                    second = None

        # Package up the color, or the two reference colors along with the mixed.
        if first:
            colors.append(first.color)
            if second is None and space is not None and space != first.color.space():
                colors[0] = first.color.convert(space)
        if second:
            colors.append(second.color)
            colors.append(first.color.compose(second.color, blend=blend_mode, space=space, out_space=space))
    except Exception:
        colors = []
    return colors


class ColorHelperBlendModeInputHandler(tools._ColorInputHandler):
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
            self.setup_color_class()
            text = self.view.substr(self.view.sel()[0])
            if text:
                color = None
                try:
                    color = self.custom_color_class(text, filters=self.filters)
                except Exception:
                    pass
                if color is not None:
                    color = Color(color)
                    return color.to_string(**util.DEFAULT)
        return ''

    def preview(self, text):
        """Preview."""

        style = self.get_html_style()

        try:
            colors = evaluate(text)

            html = ""
            for color in colors:
                pcolor = Color(color)
                message = ""
                color_string = ""
                if self.gamut_space == 'srgb':
                    check_space = self.gamut_space if pcolor.space() not in util.SRGB_SPACES else pcolor.space()
                else:
                    check_space = self.gamut_space
                if not pcolor.in_gamut(check_space):
                    pcolor.fit(self.gamut_space, in_place=True)
                    message = '<br><em style="font-size: 0.9em;">* preview out of gamut</em>'
                    color_string = "<strong>Gamut Mapped</strong>: {}<br>".format(pcolor.to_string())
                pcolor.convert(self.gamut_space, fit=True, in_place=True)
                color_string += "<strong>Color</strong>: {}".format(color.to_string(**util.DEFAULT))
                preview = pcolor.clone().set('alpha', 1)
                preview_alpha = pcolor
                preview_border = self.default_border
                temp = Color(preview_border)
                if temp.luminance() < 0.5:
                    second_border = temp.mix('white', 0.25, space=self.gamut_space, out_space=self.gamut_space)
                    second_border.set('alpha', 1)
                else:
                    second_border = temp.mix('black', 0.25, space=self.gamut_space, out_space=self.gamut_space)
                    second_border.set('alpha', 1)

                height = self.height * 3
                width = self.width * 3
                check_size = self.check_size(height, scale=8)

                html += tools.PREVIEW_IMG.format(
                    colorbox.color_box(
                        [preview, preview_alpha],
                        preview_border, second_border,
                        border_size=2, height=height, width=width, check_size=check_size
                    ),
                    message,
                    color_string
                )
            if html:
                return sublime.Html('<html><body>{}</body></html>'.format(style + html))
            else:
                return sublime.Html(
                    '<html><body>{}</body></html>'.format(mdpopups.md2html(self.view, DEF_EDIT.format(style)))
                )
        except Exception:
            return sublime.Html(mdpopups.md2html(self.view, DEF_EDIT.format(style)))

    def validate(self, color):
        """Validate."""

        try:
            color = evaluate(color)
            return len(color) > 0
        except Exception:
            return False


class ColorHelperBlendModeCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, edit, color_helper_blend_mode, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        colors = evaluate(color_helper_blend_mode)
        color = None
        if colors:
            color = colors[-1]

        if color is not None:
            if on_done is None:
                on_done = {
                    'command': 'color_helper',
                    'args': {'mode': "result", "result_type": "__tool__:__blend__"}
                }
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.COLOR_FULL_PREC)
            self.view.run_command(call, args)

    def input(self, kwargs):  # noqa: A003
        """Input."""

        return ColorHelperBlendModeInputHandler(self.view, **kwargs)
