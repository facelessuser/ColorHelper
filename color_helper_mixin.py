import sublime
import mdpopups
from . import color_helper_util as util
from .color_helper_util import GENERIC, HEX, HEX_NA
from .multiconf import get as qualify_settings
from coloraide.css import Color
from collections import namedtuple

SPACER = Color("transparent").to_string(**HEX)


class Preview(namedtuple('Preview', ['preview1', 'preview2', 'border', 'message'])):
    """Preview."""


class _ColorBoxMixin:
    """Color box mixin class."""

    def setup_gamut_style(self):
        """Setup the gamut style."""

        ch_settings = sublime.load_settings('color_helper.sublime-settings')
        self.gamut_style = ch_settings.get('gamut_style', 'lch-chroma')

    def setup_image_border(self):
        """Setup_image_border."""

        # Calculate border color for images
        border_color = Color(mdpopups.scope2style(self.view, '')['background']).convert("hsl")
        border_color.lightness = border_color.lightness + (20 if border_color.luminance() < 0.5 else 20)
        self.default_border = border_color.convert("srgb").to_string(**HEX)
        self.out_of_gamut = Color("transparent").to_string(**HEX)
        self.out_of_gamut_border = Color(self.view.style().get('redish', "red")).to_string(**HEX)

    def get_spacer(self, width=1, height=1):
        """Get a spacer."""

        return mdpopups.color_box(
            [SPACER], border_size=0,
            height=self.height * height, width=self.width * width,
            check_size=self.check_size(self.height), alpha=True
        )

    def setup_sizes(self):
        """Get sizes."""

        settings = sublime.load_settings('color_helper.sublime-settings')
        self.graphic_size = qualify_settings(settings, 'graphic_size', 'medium')
        self.graphic_scale = qualify_settings(settings, 'graphic_scale', None)

        if not isinstance(self.graphic_scale, (int, float)):
            self.graphic_scale = None

        # Calculate color box height
        self.line_height = util.get_line_height(self.view)
        top_pad = self.view.settings().get('line_padding_top', 0)
        bottom_pad = self.view.settings().get('line_padding_bottom', 0)
        if top_pad is None:
            # Sometimes we strangely get None
            top_pad = 0
        if bottom_pad is None:
            bottom_pad = 0
        box_height = self.line_height - int(top_pad + bottom_pad) - 6

        # Scale size
        if self.graphic_scale is not None:
            box_height = box_height * self.graphic_scale
            self.graphic_size = "small"
        small = max(box_height, 8)
        medium = max(box_height * 1.5, 8)
        large = max(box_height * 2, 8)
        sizes = {
            "small": (int(small), int(small)),
            "medium": (int(medium), int(medium)),
            "large": (int(large), int(large))
        }
        self.height, self.width = sizes.get(
            self.graphic_size,
            sizes["medium"]
        )

    def check_size(self, height, scale=4):
        """Get checkered size."""

        check_size = int((height - 2) / scale)
        if check_size < 2:
            check_size = 2
        return check_size

    def get_preview(self, color):
        """Get preview."""

        message = ''
        preview_border = self.default_border
        if not color.in_gamut("srgb"):
            message = 'preview out of gamut'
            if self.gamut_style in ("lch-chroma", "clip"):
                srgb = color.convert("srgb", fit=self.gamut_style)
                preview1 = srgb.to_string(**HEX_NA)
                preview2 = srgb.to_string(**HEX)
            else:
                preview1 = self.out_of_gamut
                preview2 = self.out_of_gamut
                preview_border = self.out_of_gamut_border
        else:
            srgb = color.convert("srgb")
            preview1 = srgb.to_string(**HEX_NA)
            preview2 = srgb.to_string(**HEX)

        return Preview(preview1, preview2, preview_border, message)
