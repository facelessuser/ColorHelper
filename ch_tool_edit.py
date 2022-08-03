"""Color edit tool."""
import sublime
import sublime_plugin
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

<code>Color(( percent)? + Color( percent)?)?( @colorspace)?</code>

## Instructions

Colors can be specified in any supported color space. They can<br>
be converted and output to another color space with <code>@colorspace</code>.

If two colors are provided, joined with <code>+</code>, the colors will<br>
be mixed by interpolation. When mixing, if <code>@colorspace</code> is defined<br>
at the end, colors will be mixed in that color space.

Colors are mixed at 50% unless percents are defined. If percents<br>
are defined, they must add up to 100%, if they do not, they are<br>
normalized. If only a single percent is defined, the other<br>
color will use <code>1 - percent</code>.
"""


def parse_color(base, string, start=0, second=False):
    """
    Parse colors.

    The return of `more`:
    - `None`: there is no more colors to process
    - `True`: there are more colors to process
    - `False`: there are more colors to process, but we failed to find them.
    """

    length = len(string)
    more = None
    percent = None
    space = None
    # First color
    color = base.match(string, start=start, fullmatch=False)
    if color:
        start = color.end
        if color.end != length:
            more = True
            # Percentage is provided
            m = tools.RE_PERCENT.match(string, start)
            if m:
                start = m.end(0)
                text = m.group(1)
                percent = float(text.rstrip('%'))

            # Is the first color in the input or the second?
            if not second:
                # Plus sign indicating we have an additional color to mix
                m = tools.RE_PLUS.match(string, start)
                if m:
                    start = m.end(0)
                    more = start != length
                elif percent is not None:
                    more = False
                else:
                    m = tools.RE_SPACE.match(string, start)
                    if m:
                        text = m.group(1).lower()
                        if text in color.color.CS_MAP:
                            space = text
                            start = m.end(0)
                    more = None if start == length else False
            else:
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
    return color, percent, more, space


def evaluate(base, string):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        second = None
        percent = None
        space = None

        # Try to capture the color or the two colors to mix
        first, percent1, more, space = parse_color(base, color)
        if first and more is not None:
            percent2 = None
            if more is False:
                first = None
            else:
                second, percent2, more, space = parse_color(base, color, start=first.end, second=True)
                if not second or more is False:
                    first = None
                    second = None

            # If no percents are provided, assume they are both 50%.
            if percent1 is None and percent2 is None:
                percent1 = percent2 = 0.5

            # If a percent for only one color is provided, assume the other is `1 - p`.
            elif percent1 is not None and percent2 is None:
                percent2 = (100.0 - percent1) / 100.0
                percent1 /= 100.0
            elif percent2 is not None and percent1 is None:
                percent1 = (100.0 - percent2) / 100.0
                percent2 /= 100.0
            else:
                # Normalize percentages if they do not sum to 100%.
                # Take care to handle when `p1 + p2 = 0`.
                total = (percent1 + percent2)
                if total != 100 and total != 0:
                    # Scale so both colors add up to 100%.
                    # Divide each percent by the sum total
                    p1 = percent1 / (percent1 + percent2)
                    p2 = percent2 / (percent1 + percent2)
                    percent1 = p1
                    percent2 = p2
                elif total == 0:
                    # TODO: Currently, we assume that no mixing takes place
                    #       when `p1 + p2 = 0`. What should we do?
                    raise ValueError("Undefined behavior for {} + {} = 0".format(percent1, percent2))
                else:
                    percent1 /= 100.0
                    percent2 /= 100.0

            # We only need the second as the mix function's percent
            # controls how much of the second color gets mixed in.
            percent = percent2

        if space is None and first:
            space = first.color.space()

        # Package up the color, or the two reference colors along with the mixed.
        if first:
            colors.append(first.color)
            if second is None and space is not None and space != first.color.space():
                colors[0] = first.color.convert(space)
        if second:
            colors.append(second.color)
            colors.append(first.color.mix(second.color, percent, space=space, out_space=space, premultiplied=True))
    except Exception:
        colors = []
    return colors


class ColorHelperEditInputHandler(tools._ColorInputHandler):
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
                    color = self.custom_color_class(text)
                    if color.space() not in self.filters:
                        raise ValueError('Space not in filter')
                except Exception:
                    pass
                if color is not None:
                    color = self.base(color)
                    return color.to_string(**util.DEFAULT)
        return ''

    def preview(self, text):
        """Preview."""

        style = self.get_html_style()

        try:
            colors = evaluate(self.base, text)

            html = ""
            for color in colors:
                pcolor = self.base(color)
                message = ""
                color_string = ""
                if self.gamut_space == 'srgb':
                    check_space = self.gamut_space if pcolor.space() not in util.SRGB_SPACES else pcolor.space()
                else:
                    check_space = self.gamut_space
                if not pcolor.in_gamut(check_space):
                    pcolor.fit(self.gamut_space)
                    message = '<br><em style="font-size: 0.9em;">* preview out of gamut</em>'
                    color_string = "<strong>Gamut Mapped</strong>: {}<br>".format(pcolor.to_string())
                pcolor.convert(self.gamut_space, fit=True, in_place=True)
                color_string += "<strong>Color</strong>: {}".format(color.to_string(**util.DEFAULT))
                preview = pcolor.clone().set('alpha', 1)
                preview_alpha = pcolor
                preview_border = self.default_border
                temp = self.base(preview_border)
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
            color = evaluate(self.base, color)
            return len(color) > 0
        except Exception:
            return False


class ColorHelperEditCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, edit, color_helper_edit, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        self.base = util.get_base_color()
        colors = evaluate(self.base, color_helper_edit)
        color = None
        if colors:
            color = colors[-1]

        if color is not None:
            if on_done is None:
                on_done = {
                    'command': 'color_helper',
                    'args': {'mode': "result", "result_type": "__tool__:__edit__"}
                }
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.COLOR_FULL_PREC)
            self.view.run_command(call, args)

    def input(self, kwargs):  # noqa: A003
        """Input."""

        return ColorHelperEditInputHandler(self.view, **kwargs)
