"""Color Helper tools."""
import sublime
import sublime_plugin
from .lib.coloraide import Color
import mdpopups
from . import color_helper_util as util
from .color_helper_mixin import _ColorMixin
import copy
import re

PREVIEW_IMG = '''\
<p>{}{}</p>
<p>{}</p>
'''

CONTRAST_DEMO = """
<div style="display: block; color: {}; background-color: {}; padding: 1em;">
<h2>Color Contrast</h2>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing<br>
elit, sed do eiusmod tempor incididunt ut labore et<br>
dolore magna aliqua. Ut enim ad minim veniam, quis<br>
nostrud exercitation ullamco laboris nisi ut aliquip<br>
ex ea commodo consequat.</p>
</div>
"""

RE_PLUS = re.compile(r'\s*\+\s*(?!\d)')
RE_SLASH = re.compile(r'\s*/\s*')
RE_PERCENT = re.compile(r'\s+([-+]?(?:(?:[0-9]*\.[0-9]+)|[0-9]+)%)')
RE_SPACE = re.compile(r'(?i)\s*@\s*([-a-z0-9]+)')
RE_RATIO = re.compile(r'\s+((?:(?:[0-9]*\.[0-9]+)|[0-9]+))')

STYLE = """
<style>
html {{
  margin: 0;
  padding: 0;
}}
body {{
  padding: 0.5em;
}}
br {{
  display: block;
}}
code {{
  font-style: italic;
  font-weight: bold;
  font-family: {font};
  padding: 0 0.25em;
}}
a {{
    color: inherit;
}}
div {{
  font-family: {font};
  display: block;
}}
</style>
"""

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

DEF_RATIO = """---
markdown_extensions:
- markdown.extensions.attr_list
- markdown.extensions.def_list
- pymdownx.betterem
...

{}

## Format

<code>Color( / Color)?( ratio)?</code>

## Instructions

Colors should be either an **sRGB**, **HSL**, or **HWB** color.<br>
All others will be converted to **sRGB**.

If only one color is provided, a default background<br>
of either **black** or **white** will be used.
"""

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
                percent = float(text.rstrip('%'))

            # Is the first color in the input or the second?
            if not second:
                # Plus sign indicating we have an additional color to mix
                m = RE_PLUS.match(string, start)
                if m:
                    start = m.end(0)
                    more = start != length
                elif percent is not None:
                    more = False
                else:
                    m = RE_SPACE.match(string, start)
                    if m:
                        text = m.group(1).lower()
                        if text in color.color.CS_MAP:
                            space = text
                            start = m.end(0)
                    more = None if start == length else False
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
    ratio = None
    # First color
    color = Color.match(string, start=start, fullmatch=False, filters=util.SRGB_SPACES)
    if color:
        start = color.end
        if color.end != length:
            more = True

            m = RE_RATIO.match(string, start)
            if m:
                ratio = float(m.group(1))
                start = m.end(0)

            # Is the first color in the input or the second?
            if not second and not ratio:
                # Plus sign indicating we have an additional color to mix
                m = RE_SLASH.match(string, start)
                if m and not ratio:
                    start = m.end(0)
                    more = start != length
                else:
                    more = False
            else:
                more = None if start == length else False

    if color:
        color.end = start
    return color, ratio, more


def evaluate(string):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        second = None
        percent = None
        space = None

        # Try to capture the color or the two colors to mix
        first, percent1, more, space = parse_color(color)
        if first and more is not None:
            percent2 = None
            if more is False:
                first = None
            else:
                second, percent2, more, space = parse_color(color, start=first.end, second=True)
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


def evaluate_contrast(string):
    """Evaluate color."""

    colors = []

    try:
        color = string.strip()
        second = None
        ratio = None

        # Try to capture the color or the two colors to mix
        first, ratio, more = parse_color_contrast(color)
        if first and more is not None:
            if more is False:
                first = None
            else:
                second, ratio, more = parse_color_contrast(color, start=first.end, second=True)
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
            colors.append(first)
        if second:
            if second.alpha < 1.0:
                second.alpha = 1.0
            colors.append(second)
            if ratio:
                if first.alpha < 1.0:
                    first = first.overlay(second, space="srgb")

                colormod = util.import_color("ColorHelper.custom.st_colormod.Color")
                color = colormod(
                    "color({} min-contrast({} {}))".format(
                        first.to_string(**util.FULL_PREC),
                        second.to_string(**util.FULL_PREC),
                        ratio
                    )
                )
                first = Color(color)
                colors[0] = first

            if first.alpha < 1.0:
                # Contrasted with current color
                colors.append(first.overlay(second, space="srgb"))
                # Contrasted with the two extremes min and max
                colors.append(first.overlay("white", space="srgb"))
                colors.append(first.overlay("black", space="srgb"))
            else:
                colors.append(first.clone())
    except Exception:
        colors = []
    return colors


class _ColorInputHandler(_ColorMixin, sublime_plugin.TextInputHandler):
    """Color input handler base class."""

    def __init__(self, view, on_cancel=None, **kwargs):
        """Initialize."""

        self.view = view
        self.on_cancel = on_cancel
        self.setup_gamut_style()
        self.setup_image_border()
        self.setup_sizes()

    def cancel(self):
        """On cancel."""

        if self.on_cancel is not None:
            call = self.on_cancel.get('command', 'color_helper')
            args = self.on_cancel.get('args', {})
            self.view.run_command(call, args)
        else:
            self.view.run_command('color_helper', {'mode': 'info'})

    def get_html_style(self):
        """Get HTML style."""

        styles = self.view.style()
        fg = styles['foreground']
        bg = styles['background']
        temp = Color(bg).convert("srgb")
        is_dark = temp.luminance() < 0.5
        bg = temp.mix("white" if is_dark else "black", 0.05).to_string(**util.HEX)
        code = temp.mix("white" if is_dark else "black", 0.15).to_string(**util.HEX)
        font = sublime.load_settings("Preferences.sublime-settings").get('font_face', 'Courier')
        return STYLE.format(fg=fg, bg=bg, code=code, font=font)


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
                orig = Color(color)
                message = ""
                color_string = ""
                if not orig.in_gamut('srgb'):
                    orig = orig.fit("srgb")
                    message = '<br><em style="font-size: 0.9em;">* preview out of gamut</em>'
                    color_string = "<strong>Gamut Mapped</strong>: {}<br>".format(orig.to_string())
                    srgb = orig.convert('srgb')
                else:
                    srgb = orig.convert('srgb')
                color_string += "<strong>Color</strong>: {}".format(color.to_string(**util.DEFAULT))
                preview = srgb.to_string(**util.HEX_NA)
                preview_alpha = srgb.to_string(**util.HEX)
                preview_border = self.default_border
                temp = Color(preview_border)
                if temp.luminance() < 0.5:
                    second_border = temp.mix('white', 0.25).to_string(**util.HEX_NA)
                else:
                    second_border = temp.mix('black', 0.25).to_string(**util.HEX_NA)

                height = self.height * 3
                width = self.width * 3
                check_size = self.check_size(height, scale=8)

                html += PREVIEW_IMG.format(
                    mdpopups.color_box(
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


class ColorContrastInputHandler(_ColorInputHandler):
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
                    if color.space() not in util.SRGB_SPACES:
                        color = color.convert("srgb", fit=True)
                    return color.to_string(**util.DEFAULT)
        return ''

    def preview(self, text):
        """Preview."""

        style = self.get_html_style()

        try:
            colors = evaluate_contrast(text)
            html = mdpopups.md2html(self.view, DEF_RATIO.format(style))
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
                    "<p><strong>Fg</strong>: {}</p>"
                    "<p><strong>Bg</strong>: {}</p>"
                    "<p><strong>Relative Luminance (fg)</strong>: {}</p>{}"
                    "<p><strong>Relative Luminance (bg)</strong>: {}</p>"
                ).format(
                    colors[2].to_string(**util.DEFAULT),
                    colors[1].to_string(**util.DEFAULT),
                    lum3,
                    min_max,
                    lum2
                )
                html += "<p><strong>Contrast ratio</strong>: {}</p>".format(colors[1].contrast(colors[2]))
                html += CONTRAST_DEMO.format(
                    colors[2].to_string(**util.COMMA),
                    colors[1].to_string(**util.COMMA)
                )
            return sublime.Html(style + html)
        except Exception:
            return sublime.Html(mdpopups.md2html(self.view, DEF_RATIO.format(style)))

    def validate(self, color):
        """Validate."""

        try:
            colors = evaluate_contrast(color)
            return len(colors) > 0
        except Exception:
            return False


class ColorModInputHandler(_ColorInputHandler):
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
                    srgb.fit("srgb")
                    message = '<br><em style="font-size: 0.9em;">* preview out of gamut</em>'
                preview = srgb.to_string(**util.HEX_NA)
                preview_alpha = srgb.to_string(**util.HEX)
                preview_border = self.default_border
                temp = Color(preview_border)
                if temp.luminance() < 0.5:
                    second_border = temp.mix('white', 0.25).to_string(**util.HEX_NA)
                else:
                    second_border = temp.mix('black', 0.25).to_string(**util.HEX_NA)

                height = self.height * 3
                width = self.width * 3
                check_size = self.check_size(height, scale=8)

                html = PREVIEW_IMG.format(
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
                on_done = {
                    'command': 'color_helper',
                    'args': {'mode': "result", "result_type": "__tool__:__contrast__"}
                }
            call = on_done.get('command')
            if call is None:
                return
            args = copy.deepcopy(on_done.get('args', {}))
            args['color'] = color.to_string(**util.COLOR_FULL_PREC)
            self.view.run_command(call, args)

    def input(self, kwargs):  # noqa: A003
        """Input."""

        return ColorContrastInputHandler(self.view, **kwargs)


class ColorHelperSublimeColorModCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Open edit a color directly."""

    def run(
        self, edit, color_mod, initial=None, on_done=None, **kwargs
    ):
        """Run command."""

        text = color_mod.strip()
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

        return ColorModInputHandler(self.view, **kwargs)
