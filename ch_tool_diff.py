"""Color difference tool."""
import sublime
import sublime_plugin
from .lib.coloraide import Color
import mdpopups
from . import ch_util as util
from .ch_mixin import _ColorMixin
import copy
from . import ch_tools as tools

DEF_DIFF = """---
markdown_extensions:
- markdown.extensions.attr_list
- markdown.extensions.def_list
- pymdownx.betterem
...

{}

## Format

<code>Color( - Color)?( @method)?</code>

## Instructions

Specify two colors, separated by a minus sign.<br>
Colors will be compared using Delta E 2000 unless<br>
a different method is specified.

The first color will be returned on completion.
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
    method = None
    # First color
    color = Color.match(string, start=start, fullmatch=False)
    if color:
        start = color.end
        if color.end != length:
            more = True

            m = tools.RE_MODE.match(string, start)
            if m:
                method = m.group(1)
                start = m.end(0)

            # Is the first color in the input or the second?
            if not second and not method:
                # Minus sign indicating we have an additional color to mix
                m = tools.RE_MINUS.match(string, start)
                if m and not method:
                    start = m.end(0)
                    more = start != length
                else:
                    more = False
            else:
                more = None if start == length else False

    if color:
        color.end = start
    return color, method, more


def evaluate(string):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        second = None
        method = None

        # Try to capture the color or the two colors diff
        first, method, more = parse_color(color)
        if first and more is not None:
            if more is False:
                first = None
            else:
                second, method, more = parse_color(color, start=first.end, second=True)
                if not second or more is False:
                    first = None
                    second = None
            if first:
                first = first.color
            if second:
                second = second.color
        else:
            if first:
                first = first.color

        # Package up the color, or the two reference colors along with the mixed.
        delta = 'Delta E 2000: 0'
        if method is None:
            method = "2000"
        if first:
            colors.append(first)
        if second:
            colors.append(second)
            if method == 'euclidean':
                delta = 'Distance: {}'.format(colors[0].distance(colors[1]))
            else:
                delta = 'Delta E {}: {}'.format(method, colors[0].delta_e(colors[1].to_string(), method=method))

    except Exception:
        delta = 'Delta E 2000: 0'
        colors = []
    return colors, delta


class ColorHelperDifferenceInputHandler(tools._ColorInputHandler):
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
            return '{} - {}'.format(self.color, self.color)
        elif 1 <= len(self.view.sel()) <= 2:
            self.setup_color_class()
            sels = self.view.sel()
            texts = []
            texts.append(self.view.substr(sels[0]))
            if len(sels) == 2:
                texts.append(self.view.substr(sels[1]))
            else:
                texts.append(texts[0])

            if texts:
                colors = []
                for text in texts:
                    color = None
                    try:
                        color = self.custom_color_class(text, filters=self.filters)
                    except Exception:
                        pass
                    if color is not None:
                        color = Color(color)
                        colors.append(color.to_string(**util.DEFAULT))
                if len(texts) == len(colors):
                    return ' - '.join(colors)
        return ''

    def preview(self, text):
        """Preview."""

        style = self.get_html_style()

        try:
            colors, delta = evaluate(text)
            if not colors:
                raise ValueError('No colors')
            html = mdpopups.md2html(self.view, DEF_DIFF.format(style))
            html = ""
            for color in colors:
                orig = Color(color)
                message = ""
                color_string = ""
                check_space = 'srgb' if orig.space() not in util.SRGB_SPACES else orig.space()
                if not orig.in_gamut(check_space):
                    orig = orig.fit("srgb")
                    message = '<br><em style="font-size: 0.9em;">* preview out of gamut</em>'
                    color_string = "<strong>Gamut Mapped</strong>: {}<br>".format(orig.to_string())
                srgb = orig.convert('srgb', fit=True)
                color_string += "<strong>Color</strong>: {}".format(color.to_string(**util.DEFAULT))
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

                html += tools.PREVIEW_IMG.format(
                    mdpopups.color_box(
                        [preview, preview_alpha],
                        preview_border, second_border,
                        border_size=2, height=height, width=width, check_size=check_size
                    ),
                    message,
                    color_string
                )
            if colors:
                html += delta
            return sublime.Html(style + html)
        except Exception:
            return sublime.Html(mdpopups.md2html(self.view, DEF_DIFF.format(style)))

    def validate(self, color):
        """Validate."""

        try:
            colors, _ = evaluate(color)
            return len(colors) > 0
        except Exception:
            return False


class ColorHelperDifferenceCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, edit, color_helper_difference, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        colors, _ = evaluate(color_helper_difference)
        color = None
        if colors:
            color = colors[0]

        if color is not None:
            if on_done is None:
                on_done = {
                    'command': 'color_helper',
                    'args': {'mode': "result", "result_type": "__tool__:__diff__"}
                }
                sels = self.view.sel()
                if len(sels) > 1:
                    first = sels[0]
                    sels.clear()
                    sels.add(first)
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.COLOR_FULL_PREC)
            self.view.run_command(call, args)

    def input(self, kwargs):  # noqa: A003
        """Input."""

        return ColorHelperDifferenceInputHandler(self.view, **kwargs)
