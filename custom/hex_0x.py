"""Custon color that looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""
from ..lib.coloraide.spaces.srgb.css import sRGB
from ..lib.coloraide.css import parse, serialize
import re
from ColorHelper.ch_util import get_base_color

MATCH = re.compile(r"\b0x(?:[0-9a-fA-f]{8}|[0-9a-fA-f]{6})\b")


class HexSRGB(sRGB):
    """SRGB that looks for alpha first in hex format."""

    @classmethod
    def match(cls, string, start=0, fullmatch=True):
        """Match a CSS color string."""

        m = MATCH.match(string, start)
        if m is not None and (not fullmatch or m.end(0) == len(string)):
            return parse.parse_hex(m.group(0).replace('0x', '#', 1)), m.end(0)
        return None

    @classmethod
    def to_string(
        cls, parent, *, alpha=None, precision=None, fit=True, none=False, **kwargs
    ):
        """Convert to CSS."""

        h = serialize.serialize_css(
            parent,
            alpha=alpha,
            precision=precision,
            fit=fit,
            hexa=True,
            upper=kwargs.get('upper', False)
        )

        return h.replace('#', '0x', 1)


class ColorHex(get_base_color()):
    """Color object whose sRGB color space looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""


ColorHex.register(HexSRGB, overwrite=True)
