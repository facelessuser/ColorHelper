"""Color Helper tools."""
import sublime
import sublime_plugin
from .lib.coloraide import Color
from . import ch_util as util
from .ch_mixin import _ColorMixin
import re

PREVIEW_IMG = '''\
<p>{}{}</p>
<p>{}</p>
'''

RE_PLUS = re.compile(r'\s*\+\s*(?!\d)')
RE_SLASH = re.compile(r'\s*/\s*')
RE_PERCENT = re.compile(r'\s+([-+]?(?:(?:[0-9]*\.[0-9]+)|[0-9]+)%)')
RE_SPACE = re.compile(r'(?i)\s*@\s*([-a-z0-9]+)')
RE_RATIO = re.compile(r'\s+((?:(?:[0-9]*\.[0-9]+)|[0-9]+))')
RE_MINUS = re.compile(r'\s*\-\s*(?!\d)')
RE_MODE = re.compile(r'(?i)\s*!\s*([-a-z0-9]+)')

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
        bg = temp.mix("white" if is_dark else "black", 0.05, space="srgb").to_string(**util.HEX)
        code = temp.mix("white" if is_dark else "black", 0.15, space="srgb").to_string(**util.HEX)
        font = sublime.load_settings("Preferences.sublime-settings").get('font_face', 'Courier')
        return STYLE.format(fg=fg, bg=bg, code=code, font=font)
