"""Custon color that looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""
from ..lib.coloraide import Color
from ..lib.coloraide.spaces.srgb.css import SRGB
from ..lib.coloraide import parse
from ..lib.coloraide import util
import re


class ASRGB(SRGB):
    """SRGB that looks for alpha first in hex format."""

    MATCH = re.compile(r"(?i)\#(?:{hex}{{8}}|{hex}{{6}})\b".format(**parse.COLOR_PARTS))

    @classmethod
    def match(cls, string, start=0, fullmatch=True):
        """Match a CSS color string."""

        m = cls.MATCH.match(string, start)
        if m is not None and (not fullmatch or m.end(0) == len(string)):
            return cls.split_channels(m.group(0)), m.end(0)
        return None

    @classmethod
    def translate_channel(cls, channel, value):
        """Translate channel string."""

        if -1 <= channel <= 2:
            return parse.norm_hex_channel(value)

    @classmethod
    def split_channels(cls, color):
        """Split channels."""

        if len(color) == 9:
            return cls.null_adjust(
                (
                    cls.translate_channel(0, "#" + color[3:5]),
                    cls.translate_channel(1, "#" + color[5:7]),
                    cls.translate_channel(2, "#" + color[7:])
                ),
                cls.translate_channel(-1, "#" + color[1:3]),
            )
        else:
            return cls.null_adjust(
                (
                    cls.translate_channel(0, "#" + color[1:3]),
                    cls.translate_channel(1, "#" + color[3:5]),
                    cls.translate_channel(2, "#" + color[5:])
                ),
                1.0
            )

    def to_string(
        self, parent, *, options=None, alpha=None, precision=None, fit=True, none=False, **kwargs
    ):
        """Convert to Hex format."""

        options = kwargs
        a = util.no_nan(self.alpha)
        show_alpha = alpha is not False and (alpha is True or a < 1.0)

        template = "#{:02x}{:02x}{:02x}{:02x}" if show_alpha else "#{:02x}{:02x}{:02x}"
        if options.get("upper"):
            template = template.upper()

        # Always fit hex
        method = None if not isinstance(fit, str) else fit
        coords = util.no_nan(parent.fit(method=method).coords())
        if show_alpha:
            value = template.format(
                int(util.round_half_up(a * 255.0)),
                int(util.round_half_up(coords[0] * 255.0)),
                int(util.round_half_up(coords[1] * 255.0)),
                int(util.round_half_up(coords[2] * 255.0))
            )
        else:
            value = template.format(
                int(util.round_half_up(coords[0] * 255.0)),
                int(util.round_half_up(coords[1] * 255.0)),
                int(util.round_half_up(coords[2] * 255.0))
            )
        return value


class ColorAlphaHex(Color):
    """Color object whose sRGB color space looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""


ColorAlphaHex.register(ASRGB, overwrite=True)
