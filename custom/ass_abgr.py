"""Custom color that looks for colors of format `&HAABBGGRR` as `#AARRGGBB`."""
from ..lib.coloraide import algebra as alg
from ..lib.coloraide.css import parse
from ..lib.coloraide.spaces.srgb.css import sRGB
import re
from ColorHelper.ch_util import get_base_color

MATCH = re.compile(r"(?P<prefix>&H)?(?P<color>[0-9a-fA-F]{1,8})(?P<suffix>&|\b)")


def split_channels(color: str):
    """Split string into the appropriate channels."""

    # convert `RR` / `GGRR` / `BBGGRR` to `AABBGGRR`
    # consecutive leading 0s can be omitted and the alpha is 00 (opaque) by default
    color = color.zfill(8)

    # deal with `AABBGGRR`
    if len(color) == 8:
        return (
            (
                parse.norm_hex_channel(color[6:]),  # RR
                parse.norm_hex_channel(color[4:6]),  # GG
                parse.norm_hex_channel(color[2:4]),  # BB
            ),
            1 - parse.norm_hex_channel(color[:2]),  # AA
        )

    raise RuntimeError("Something is wrong in code logics.")


class AssABGR(sRGB):
    """ASS `ABGR` color space."""

    @classmethod
    def match(cls, string: str, start: int = 0, fullmatch: bool = True):
        """Match a color string."""

        m = MATCH.match(string, start)
        if m is not None and (not fullmatch or m.end(0) == len(string)):
            return split_channels(m.group("color")), m.end(0)
        return None

    @classmethod
    def to_string(cls, parent, *, options=None, alpha=None, precision=None, fit=True, none=False, **kwargs):
        """Convert color to `&HAABBGGRR`."""

        options = kwargs
        a = alg.no_nan(parent[-1])
        show_alpha = alpha is not False and (alpha is True or a < 1.0)

        template = "&H{:02x}{:02x}{:02x}{:02x}" if show_alpha else "&H{:02x}{:02x}{:02x}"
        if options.get("upper"):
            template = template.upper()

        # Always fit hex
        method = None if not isinstance(fit, str) else fit
        coords = alg.no_nans(parent.clone().fit(method=method)[:-1])
        if show_alpha:
            value = template.format(
                int(alg.round_half_up(a * 255.0)),
                int(alg.round_half_up(coords[2] * 255.0)),
                int(alg.round_half_up(coords[1] * 255.0)),
                int(alg.round_half_up(coords[0] * 255.0)),
            )
        else:
            value = template.format(
                int(alg.round_half_up(coords[2] * 255.0)),
                int(alg.round_half_up(coords[1] * 255.0)),
                int(alg.round_half_up(coords[0] * 255.0)),
            )
        return value


class ColorAssABGR(get_base_color()):
    """Color class for ASS `ABGR` colors."""


ColorAssABGR.register(AssABGR, overwrite=True)
