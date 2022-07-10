"""Custon color that looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""
from ..lib.coloraide import Color
from ..lib.coloraide.spaces.srgb.css import SRGB
from ..lib.coloraide.css import parse
from ..lib.coloraide import algebra as alg
import re

MATCH = re.compile(r"(?i)\#(?:{hex}{{8}}|{hex}{{6}})\b".format(**parse.COLOR_PARTS))


def split_channels(color):
    """Split channels."""

    if len(color) == 9:
        return (
            (
                parse.norm_hex_channel(color[3:5]),
                parse.norm_hex_channel(color[5:7]),
                parse.norm_hex_channel(color[7:])
            ),
            parse.norm_hex_channel(color[1:3]),
        )
    else:
        return (
            (
                parse.norm_hex_channel(color[1:3]),
                parse.norm_hex_channel(color[3:5]),
                parse.norm_hex_channel(color[5:])
            ),
            1.0
        )


class ASRGB(SRGB):
    """SRGB that looks for alpha first in hex format."""

    COLOR_FORMAT = False

    @classmethod
    def match(cls, string, start=0, fullmatch=True):
        """Match a CSS color string."""

        m = MATCH.match(string, start)
        if m is not None and (not fullmatch or m.end(0) == len(string)):
            return split_channels(m.group(0)), m.end(0)
        return None

    @classmethod
    def to_string(
        cls, parent, *, options=None, alpha=None, precision=None, fit=True, none=False, **kwargs
    ):
        """Convert to Hex format."""

        options = kwargs
        a = alg.no_nan(parent[-1])
        show_alpha = alpha is not False and (alpha is True or a < 1.0)

        template = "#{:02x}{:02x}{:02x}{:02x}" if show_alpha else "#{:02x}{:02x}{:02x}"
        if options.get("upper"):
            template = template.upper()

        # Always fit hex
        method = None if not isinstance(fit, str) else fit
        coords = alg.no_nans(parent.clone().fit(method=method)[:-1])
        if show_alpha:
            value = template.format(
                int(alg.round_half_up(a * 255.0)),
                int(alg.round_half_up(coords[0] * 255.0)),
                int(alg.round_half_up(coords[1] * 255.0)),
                int(alg.round_half_up(coords[2] * 255.0))
            )
        else:
            value = template.format(
                int(alg.round_half_up(coords[0] * 255.0)),
                int(alg.round_half_up(coords[1] * 255.0)),
                int(alg.round_half_up(coords[2] * 255.0))
            )
        return value


class ColorAlphaHex(Color):
    """Color object whose sRGB color space looks for colors of format `#RRGGBBAA` as `#AARRGGBB`."""


ColorAlphaHex.register(ASRGB, overwrite=True)
