"""Color Helper tools."""
import sublime
import sublime_plugin
from coloraide.css import Color
import mdpopups
from . import color_helper_util as util
from .color_helper_mixin import _ColorMixin
import copy
import re

PREVIEW_IMG = '''\
<p>{}{}</p>
<p>{}</p>
'''

CONTRAST_DEMO = """\
<style>
div {{
    display: block;
    color: {};
    background-color: {};
    padding: 2em;
}}
</style>
<div>
<h2>Color Contrast</h2>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis
aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint
occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
</p>
</div>
"""

RE_PLUS = re.compile(r'\s*\+\s*')
RE_RATIO = re.compile(r'\s*/\s*')
RE_PERCENT = re.compile(r'\s+((?:(?:[0-9]*\.[0-9]+)|[0-9]+)%)')
RE_SPACE = re.compile(r'(?i)\s*@\s*([-a-z0-9]+)')


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
    percent = None
    space = None
    # First color
    color = Color.match(string, start=start, fullmatch=False)
    if color:
        start = color.end
        if color.end != length:
            more = True
            # Percentage if provided
            m = RE_PERCENT.match(string, start)
            if m:
                start = m.end(0)
                text = m.group(1)
                percent = float(text.rstrip('%')) / 100.0

            # Is the first color in the input or the second?
            if not second:
                # Plus sign indicating we have an additional color to mix
                m = RE_PLUS.match(string, start)
                if m:
                    start = m.end(0)
                    more = start != length
                else:
                    more = False
            else:
                # Color space indicator
                m = RE_SPACE.match(string, start)
                if m:
                    text = m.group(1).lower()
                    if text in color.color.CS_MAP:
                        space = text
                        start = m.end(0)
                more = None if start == length else False

    if color:
        color.end = start
    return color, percent, more, space


def parse_color_contrast(string, start=0, second=False):
    """
    Parse colors.

    The return of `more`:
    - `None`: there is no more colors to process
    - `True`: there are more colors to process
    - `False`: there are more colors to process, but we failed to find them.
    """

    length = len(string)
    more = None
    # First color
    color = Color.match(string, start=start, fullmatch=False, filters=util.SRGB_SPACES)
    if color:
        start = color.end
        if color.end != length:
            more = True

            # Is the first color in the input or the second?
            if not second:
                # Plus sign indicating we have an additional color to mix
                m = RE_RATIO.match(string, start)
                if m:
                    start = m.end(0)
                    more = start != length
                else:
                    more = False
            else:
                more = None if start == length else False

    if color:
        color.end = start
    return color, more


def evaluate(string):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        second = None
        percent = None
        space = None

        # Try to capture the color or the two colors to mix
        first, percent1, more = parse_color(color)[:3]
        if first and more is not None:
            percent2 = None
            if more is False:
                first = None
            else:
                second, percent2, more, space = parse_color(color, start=first.end, second=True)
                if not second or more is False:
                    first = None
                    second = None

            # - Percents less than zero should be clamped to zero
            # - If a percent for only one color is provided, assume
            #   the other is 1 - p.
            # - Two percents are provided and they do not equal 100%
            #   scale them until they do.
            # - If no percents are provided, assume they are both 50%.
            if percent1 is None and percent2 is None:
                percent1 = 0.5
                percent2 = 0.5
            elif percent1 is not None and percent2 is None:
                percent1 = max(min(percent1, 1.0), 0.0)
                percent2 = 1.0 - percent1
            elif percent2 is not None and percent1 is None:
                percent2 = max(min(percent2, 1.0), 0.0)
                percent1 = 1.0 - percent2
            else:
                percent1 = max(percent1, 0.0)
                percent2 = max(percent2, 0.0)
                total = (percent1 + percent2)
                if total == 0.0:
                    percent1 = 0.5
                    percent2 = 0.5
                elif total != 1.0:
                    factor = 1.0 / total
                    percent1 *= factor
                    percent2 *= factor

            # We only need the seconds as the mix function's percent
            # controls how much of the second color gets mixed in.
            percent = percent2

        # Package up the color, or the two reference colors along with the mixed.
        if first:
            colors.append(first.color)
        if second:
            colors.append(second.color)
            colors.append(first.color.mix(second.color, percent, alpha=True, space=space))
    except Exception:
        colors = []
    return colors


def evaluate_contrast(string):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        second = None

        # Try to capture the color or the two colors to mix
        first, more = parse_color_contrast(color)
        if first and more is not None:
            if more is False:
                first = None
            else:
                second, more = parse_color_contrast(color, start=first.end, second=True)
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
                second = Color("white" if first.luminance() < 0.5 else "black")

        # Package up the color, or the two reference colors along with the mixed.
        if first:
            colors.append(first.convert("srgb"))
        if second:
            if second.alpha < 1.0:
                second.alpha = 1.0
            colors.append(second)
            if first.alpha < 1.0:
                # Contrasted with current color
                colors.append(first.alpha_composite(second, space="srgb"))
                # Contrasted with the two extremes min and max
                colors.append(first.alpha_composite("white", space="srgb"))
                colors.append(first.alpha_composite("black", space="srgb"))
            else:
                colors.append(first.convert("srgb"))
    except Exception:
        colors = []
    return colors


class _ColorInputHandler(_ColorMixin, sublime_plugin.TextInputHandler):
    """Color input handler base class."""

    def __init__(self, view, on_cancel=None, **kwargs):
        """Initialize."""

        self.view = view
        self.on_cancel = on_cancel
        self.setup_image_border()
        self.setup_gamut_style()
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

        return "Color [+ Color]?"

    def initial_text(self):
        """Initial text."""

        self.setup_color_class()
        if self.color is not None:
            return self.color
        elif len(self.view.sel()) == 1:
            text = self.view.substr(self.view.sel()[0])
            if text:
                color = None
                try:
                    color = self.custom_color_class(text, filters=self.filters)
                except Exception:
                    pass
                if color is not None:
                    color = Color(color)
                    return color.to_string()
        return ''

    def preview(self, text):
        """Preview."""

        try:
            colors = evaluate(text)

            html = ""
            for color in colors:
                srgb = Color(color).convert("srgb")
                preview_border = self.default_border
                message = ""
                if not srgb.in_gamut():
                    srgb.fit("srgb", method=self.preferred_gamut_mapping)
                    message = '<br><em style="font-size: 0.9em;">* preview out of gamut</em>'
                preview = srgb.to_string(**util.HEX_NA)
                preview_alpha = srgb.to_string(**util.HEX)
                preview_border = self.default_border

                height = self.height * 3
                width = self.width * 3
                check_size = self.check_size(height, scale=8)

                html += PREVIEW_IMG.format(
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
        except Exception:
            return ""

    def validate(self, color):
        """Validate."""

        try:
            color = evaluate(color)
            return len(color) > 0
        except Exception:
            return False


class ColorContrastInputHandler(_ColorInputHandler):
    """Handle color inputs."""

    def __init__(self, view, initial=None, **kwargs):
        """Initialize."""

        self.color = initial
        super().__init__(view, **kwargs)

    def placeholder(self):
        """Placeholder."""

        return "Color / Color"

    def initial_text(self):
        """Initial text."""

        self.setup_color_class()
        if self.color is not None:
            return self.color
        elif len(self.view.sel()) == 1:
            text = self.view.substr(self.view.sel()[0])
            if text:
                color = None
                try:
                    color = self.custom_color_class(text, filters=self.filters)
                except Exception:
                    pass
                if color is not None:
                    color = Color(color)
                    if color.space() not in util.SRGB_SPACES:
                        color = color.convert("srgb", fit=self.preferred_gamut_mapping)
                    return color.to_string()
        return ''

    def preview(self, text):
        """Preview."""

        try:
            colors = evaluate_contrast(text)

            html = ""
            if len(colors) >= 3:
                lum2 = colors[1].luminance()
                lum3 = colors[2].luminance()
                if len(colors) > 3:
                    luma = colors[3].luminance()
                    lumb = colors[4].luminance()
                    mn = min(luma, lumb)
                    mx = max(luma, lumb)
                    min_max = "<ul><li><strong>min</strong>: {}</li><li><strong>max</strong>: {}</li></ul>".format(
                        mn, mx
                    )
                else:
                    min_max = ""
                html = (
                    "<br><br><p><strong>Relative Luminance (fg)</strong>: {}</p>{}"
                    "<p><strong>Relative Luminance (bg)</strong>: {}</p>"
                ).format(
                    lum3, min_max, lum2
                )
                html += "<p><strong>Contrast ratio</strong>: {}</p>".format(colors[1].contrast_ratio(colors[2]))
                html += CONTRAST_DEMO.format(
                    colors[2].to_string(comma=True),
                    colors[1].to_string(comma=True)
                )
            return sublime.Html(html)
        except Exception:
            return ""

    def validate(self, color):
        """Validate."""

        return True
        try:
            colors = evaluate_contrast(color)
            return len(colors) > 0
        except Exception:
            return False


class ColorHelperEditCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, edit, color, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        colors = evaluate(color)
        color = None
        if colors:
            color = colors[-1]

        if color is not None:
            if on_done is None:
                on_done = {'command': 'color_helper', 'args': {'mode': "color_picker_result"}}
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.GENERIC)
            self.view.run_command(call, args)

    def input(self, kwargs):  # noqa: A003
        """Input."""

        return ColorInputHandler(self.view, **kwargs)


class ColorHelperContrastRatioCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, edit, color_contrast, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        colors = evaluate_contrast(color_contrast)
        color = None
        if colors:
            color = colors[0]

        if color is not None:
            if on_done is None:
                on_done = {'command': 'color_helper', 'args': {'mode': "color_picker_result"}}
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.GENERIC)
            self.view.run_command(call, args)

    def input(self, kwargs):  # noqa: A003
        """Input."""

        return ColorContrastInputHandler(self.view, **kwargs)
