import sublime
import sublime_plugin
from coloraide.css import Color
import mdpopups
from .multiconf import get as qualify_settings
from . import color_helper_util as util
from .color_helper_mixin import _ColorMixin
import copy
import re

PREVIEW_IMG = '''\
<p>{}{}</p>
<p>{}</p>
'''

RE_PLUS = re.compile(r'\s*\+\s*')
RE_PERCENT = re.compile(r'\s+((?:(?:[0-9]*\.[0-9]+)|[0-9]+)%)')
RE_SPACE = re.compile(r'(?i)\s*/\s*([-a-z0-9]+)')


def parse_color(string, color_class, start=0, second=False):
    """Parse color."""

    length = len(string)
    more = None
    percent = None
    space = None
    color = color_class.match(string, start=start, fullmatch=False)
    if color:
        start = color.end
        if color.end != length:
            more = True
            m = RE_PERCENT.match(string, start)
            if m:
                start = m.end(0)
                text = m.group(1)
                percent = float(text.rstrip('%')) / 100.0
            if not second:
                m = RE_PLUS.match(string, start)
                if m:
                    start = m.end(0)
                    more = start != length
                else:
                    more = False
            else:
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


def evaluate(string, color_class):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        length = len(color)
        second = None
        percent = 0.5
        space = None
        first, percent1, more = parse_color(color, color_class)[:3]
        if first and more is not None:
            percent2 = None
            if more is False:
                first = None
            else:
                second, percent2, more, space = parse_color(color, color_class, start=first.end, second=True)
                if not second or more is False:
                    first = None
                    second = None
            if percent1 is not None:
                percent = 1.0 - max(min(percent1, 100.0), 0.0)
            elif percent2 is not None:
                percent = max(min(percent2, 100.0), 0.0)

        if first:
            colors.append(first.color)
        if second:
            colors.append(second.color)
            colors.append(first.color.clone().mix(second.color, percent, alpha=True, space=space))
    except Exception:
        import traceback
        print(traceback.format_exc())
        pass
    return colors


class _ColorInputHandler(_ColorMixin, sublime_plugin.TextInputHandler):
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

        self.setup_color_class()
        if self.color is not None:
            self.custom_color_class = Color
            return self.color
        elif len(self.view.sel()) == 1:
            return self.view.substr(self.view.sel()[0])

    def preview(self, text):
        """Preview."""

        try:
            colors = evaluate(text, self.custom_color_class)

            html = ""
            for color in colors:
                srgb = Color(color).convert("srgb")
                preview_border = self.default_border
                message = ""
                if not srgb.in_gamut():
                    srgb.fit("srgb")
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
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return ""

    def validate(self, color):
        """Validate."""

        try:
            color = evaluate(color, self.custom_color_class)
            return len(color) > 0
        except Exception:
            import traceback
            print(traceback.format_exc())
            return False


class ColorHelperEditCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, view, color, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        if initial is None:
            self.setup_color_class()
            colors = evaluate(color, self.custom_color_class)
            if colors:
                color = Color(colors[-1])
        else:
            color = Color(color)

        if color is not None:
            if on_done is None:
                on_done = {'command': 'color_helper', 'args': {'mode': "color_picker_result"}}
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.GENERIC)
            self.view.run_command(call, args)

    def input(self, kwargs):
        """Input."""

        return ColorInputHandler(self.view, **kwargs)
