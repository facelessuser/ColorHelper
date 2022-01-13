"""Custon color that looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""
from ..lib.coloraide import Color
from ..lib.coloraide.spaces.srgb.css import SRGB
from ..lib.coloraide import parse
from ..lib.coloraide import util
import re


def norm_hex_channel(string):
    """Normalize the hex string to a form we can handle."""

    if string.startswith('0x'):
        return int(string[2:], 16) * parse.RGB_CHANNEL_SCALE
    else:
        raise ValueError("String format of a hex channel must be in the form of '0xXX'")


class HexSRGB(SRGB):
    """SRGB that looks for alpha first in hex format."""

    MATCH = re.compile(r"\b0x(?:[0-9a-fA-f]{8}|[0-9a-fA-f]{6})\b")

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

        # Unless it explicitly starts with `0x` we will assume it is a int/float.
        if -1 <= channel <= 2:
            return norm_hex_channel(value)

    @classmethod
    def split_channels(cls, color):
        """Split channels."""

        return cls.null_adjust(
            (
                cls.translate_channel(0, '0x' + color[2:4]),
                cls.translate_channel(1, '0x' + color[4:6]),
                cls.translate_channel(2, '0x' + color[6:8])
            ),
            cls.translate_channel(-1, '0x' + color[8:]) if len(color) > 8 else 1.0
        )

    def to_string(
        self, parent, *, options=None, alpha=None, precision=None, fit=True, none=False, **kwargs
    ):
        """Convert to Hex format."""

        options = kwargs
        a = util.no_nan(self.alpha)
        show_alpha = alpha is not False and (alpha is True or a < 1.0)

        template = "0x{:02x}{:02x}{:02x}{:02x}" if show_alpha else "0x{:02x}{:02x}{:02x}"
        if options.get("upper"):
            template = template.upper()

        method = None if not isinstance(fit, str) else fit
        coords = util.no_nans(parent.fit(method=method).coords())
        if show_alpha:
            value = template.format(
                int(util.round_half_up(coords[0] * 255.0)),
                int(util.round_half_up(coords[1] * 255.0)),
                int(util.round_half_up(coords[2] * 255.0)),
                int(util.round_half_up(a * 255.0))
            )
        else:
            value = template.format(
                int(util.round_half_up(coords[0] * 255.0)),
                int(util.round_half_up(coords[1] * 255.0)),
                int(util.round_half_up(coords[2] * 255.0))
            )
        return value


class ColorHex(Color):
    """Color object whose sRGB color space looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""


ColorHex.register(HexSRGB, overwrite=True)
