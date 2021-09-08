"""Custom color that looks for colors of format `&HAABBGGRR` as `#AARRGGBB`."""
from ColorHelper.lib.coloraide import Color
from ColorHelper.lib.coloraide import util
from ColorHelper.lib.coloraide.spaces import _parse
from ColorHelper.lib.coloraide.spaces.srgb.css import SRGB
import copy
import re


class AssABGR(SRGB):
    """ASS `ABGR` color space."""

    MATCH = re.compile(r"(?P<prefix>&H)?(?P<color>[0-9a-fA-F]{1,8})(?P<suffix>&|\b)")

    @classmethod
    def match(cls, string: str, start: int = 0, fullmatch: bool = True):
        """Match a color string."""

        m = cls.MATCH.match(string, start)
        if m is not None and (not fullmatch or m.end(0) == len(string)):
            return cls.split_channels(m.group("color")), m.end(0)
        return None, None

    @classmethod
    def translate_channel(cls, channel: int, value: str):
        """Translate channel string."""

        if -1 <= channel <= 2:
            return _parse.norm_hex_channel(value)

    @classmethod
    def split_channels(cls, color: str):
        """Split string into the appropriate channels."""

        # convert `RR` / `GGRR` / `BBGGRR` to `AABBGGRR`
        # consecutive leading 0s can be omitted and the alpha is 00 (opaque) by default
        color = color.zfill(8)

        # deal with `AABBGGRR`
        if len(color) == 8:
            return cls.null_adjust(
                (
                    cls.translate_channel(0, "#" + color[6:]),  # RR
                    cls.translate_channel(1, "#" + color[4:6]),  # GG
                    cls.translate_channel(2, "#" + color[2:4]),  # BB
                ),
                1 - cls.translate_channel(-1, "#" + color[:2]),  # AA
            )

        raise RuntimeError("Something is wrong in code logics.")

    def to_string(self, parent, *, options=None, alpha=None, precision=None, fit=True, **kwargs):
        """Convert color to `&HAABBGGRR`."""

        options = kwargs
        a = util.no_nan(self.alpha)
        show_alpha = alpha is not False and (alpha is True or a < 1.0)

        template = "&H{:02x}{:02x}{:02x}{:02x}" if show_alpha else "&H{:02x}{:02x}{:02x}"
        if options.get("upper"):
            template = template.upper()

        # Always fit hex
        method = None if not isinstance(fit, str) else fit
        coords = util.no_nan(parent.fit(method=method).coords())
        if show_alpha:
            value = template.format(
                int(util.round_half_up(a * 255.0)),
                int(util.round_half_up(coords[2] * 255.0)),
                int(util.round_half_up(coords[1] * 255.0)),
                int(util.round_half_up(coords[0] * 255.0)),
            )
        else:
            value = template.format(
                int(util.round_half_up(coords[2] * 255.0)),
                int(util.round_half_up(coords[1] * 255.0)),
                int(util.round_half_up(coords[0] * 255.0)),
            )
        return value


class ColorAssABGR(Color):
    """Color class for ASS `ABGR` colors."""

    CS_MAP = copy.copy(Color.CS_MAP)
    CS_MAP["srgb"] = AssABGR
