"""Mix-in class."""
import sublime
from . lib import colorbox
from . import ch_util as util
from .ch_util import GAMUT_SPACES
from .lib.multiconf import get as qualify_settings
from .lib.coloraide import Color
from collections import namedtuple

SPACER = Color("transparent")


class Preview(namedtuple('Preview', ['preview1', 'preview2', 'border', 'message'])):
    """Preview."""


class _ColorMixin:
    """Color box mix-in class."""

    def setup_gamut_style(self):
        """Setup the gamut style."""

        ch_settings = sublime.load_settings('color_helper.sublime-settings')
        self.show_out_of_gamut_preview = ch_settings.get('show_out_of_gamut_preview', True)
        self.gamut_space = ch_settings.get('gamut_space', 'srgb')
        if self.gamut_space not in GAMUT_SPACES:
            self.gamut_space = 'srgb'

    def setup_image_border(self):
        """Setup_image_border."""

        ch_settings = sublime.load_settings('color_helper.sublime-settings')
        border_color = ch_settings.get('image_border_color')
        if border_color is not None:
            try:
                border_color = self.base(border_color)
                border_color.fit(self.gamut_space)
            except Exception:
                border_color = None

        if border_color is None:
            # Calculate border color for images
            border_color = self.base(
                self.view.style()['background'],
            ).convert("hsl")
            border_color['lightness'] = border_color['lightness'] + (0.3 if border_color.luminance() < 0.5 else -0.3)

        self.default_border = border_color.convert(self.gamut_space, in_place=True)
        self.out_of_gamut = self.base("transparent").convert(self.gamut_space, in_place=True)
        self.out_of_gamut_border = self.base(
            self.view.style().get('redish', "red"),
        ).convert(self.gamut_space, in_place=True)

    def get_color_options(self, pt, rule):
        """Get color class based on selection scope."""

        self.color_classes = util.get_settings_colors()
        classes = rule.get("color_class", [])

        # Check if the first point within the color matches our scope rules
        # and load up the appropriate color class
        color_class = self.base
        filters = []
        output = []
        edit_mode = "default"
        for item in classes:
            try:
                value = self.view.score_selector(pt, item["scopes"])
                if not value:
                    continue
                else:
                    class_options = self.color_classes.get(item["class"])
                    if class_options is None:
                        continue
                    module = class_options.get("class", "ColorHelper.lib.coloraide.Color")
                    if isinstance(module, str):
                        if module == "ColorHelper.lib.coloraide.Color":
                            # Use the base
                            color_class = self.base
                        else:
                            # Initialize the color module and cache it for this view
                            color_class = util.import_color(module)
                        class_options["class"] = color_class
                    else:
                        color_class = module
                    filters = class_options.get("filters", [])
                    output = class_options.get("output", [])
                    edit_mode = class_options.get('edit_mode', 'default')
                    if edit_mode not in ('default', 'st-colormod'):
                        edit_mode = 'default'
                    break
            except Exception:
                color_class = self.base
                filters = []
                output = []
                edit_mode = 'default'
        return color_class, filters, output, edit_mode

    def setup_color_class(self):
        """Get the color class for the view."""

        sels = self.view.sel()
        pt = 0
        if len(sels) >= 1:
            pt = sels[0].begin()
        rule = util.get_rules(self.view)
        if rule is None:
            rule = {}
        color_class, filters, output, edit_mode = self.get_color_options(pt, rule)
        self.edit_mode = edit_mode
        self.custom_color_class = color_class
        self.filters = filters
        self.output_options = output
        self.color_class = self.base
        try:
            self.color_trigger = rule.get("color_trigger", util.RE_COLOR_START)
        except Exception:
            self.color_trigger = util.RE_COLOR_START

    def get_spacer(self, width=1, height=1):
        """Get a spacer."""

        return colorbox.color_box(
            [SPACER.convert(self.gamut_space)], border_size=0,
            height=self.height * height, width=self.width * width,
            check_size=self.check_size(self.height), alpha=True,
            gamut_space=self.gamut_space
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
        box_height = self.line_height - int(top_pad + bottom_pad)

        # Scale size
        if self.graphic_scale is not None:
            box_height = box_height * self.graphic_scale
            self.graphic_size = "medium"
            sizes = {"medium": (int(box_height), int(box_height))}
        else:
            small = max(box_height * 0.75, 8)
            medium = max(box_height * 1, 8)
            large = max(box_height * 1.25, 8)
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
        if self.gamut_space == 'srgb':
            check_space = self.gamut_space if color.space() not in util.SRGB_SPACES else color.space()
        else:
            check_space = self.gamut_space
        if not color.in_gamut(check_space):
            message = 'preview out of gamut'
            if self.show_out_of_gamut_preview:
                pcolor = color.convert(self.gamut_space, fit=True)
                preview1 = pcolor.clone().set('alpha', 1)
                preview2 = pcolor
            else:
                preview1 = self.out_of_gamut
                preview2 = self.out_of_gamut
                preview_border = self.out_of_gamut_border
        else:
            pcolor = color.convert(self.gamut_space, fit=True)
            preview1 = pcolor.clone().set('alpha', 1)
            preview2 = pcolor

        return Preview(preview1, preview2, preview_border, message)
