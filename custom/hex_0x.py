"""Custon color that looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""
from coloraide.colors import Color, SRGB
from coloraide.colors import _parse as parse
from coloraide import util
import copy
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
        return None, None

    @classmethod
    def _tx_channel(cls, channel, value):
        """Translate channel string."""

        # Unless it explicitly starts with `0x` we will assume it is a int/float.
        if -1 <= channel <= 2:
            return norm_hex_channel(value)

    @classmethod
    def split_channels(cls, color):
        """Split channels."""

        return [
            cls._tx_channel(0, '0x' + color[2:4]),
            cls._tx_channel(1, '0x' + color[4:6]),
            cls._tx_channel(2, '0x' + color[6:8]),
            cls._tx_channel(-1, '0x' + color[8:]) if len(color) > 8 else 1.0
        ]

    def to_string(
        self, *, options=None, alpha=None, precision=util.DEF_PREC, fit=util.DEF_FIT, **kwargs
    ):
        """Convert to Hex format."""

        if options is None:
            options = {}

        show_alpha = alpha is not False and (alpha is True or self._alpha < 1.0)

        template = "0x{:02x}{:02x}{:02x}{:02x}" if show_alpha else "0x{:02x}{:02x}{:02x}"
        if options.get("hex_upper"):
            template = template.upper()

        coords = self.fit_coords(method=fit) if fit else self.coords()
        if show_alpha:
            value = template.format(
                int(util.round_half_up(coords[0] * 255.0)),
                int(util.round_half_up(coords[1] * 255.0)),
                int(util.round_half_up(coords[2] * 255.0)),
                int(util.round_half_up(self._alpha * 255.0))
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

    CS_MAP = copy.copy(Color.CS_MAP)
    CS_MAP["srgb"] = HexSRGB
