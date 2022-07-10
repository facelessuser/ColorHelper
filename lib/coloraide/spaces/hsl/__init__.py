"""HSL class."""
from ...spaces import Space, Cylindrical
from ...cat import WHITES
from ...channels import Channel, FLG_ANGLE, FLG_PERCENT
from ... import util
from ... import algebra as alg
from ...types import Vector


def srgb_to_hsl(rgb: Vector) -> Vector:
    """SRGB to HSL."""

    r, g, b = rgb
    mx = max(rgb)
    mn = min(rgb)
    h = alg.NaN
    s = 0.0
    l = (mn + mx) / 2
    c = mx - mn

    if c != 0.0:
        if mx == r:
            h = (g - b) / c
        elif mx == g:
            h = (b - r) / c + 2.0
        else:
            h = (r - g) / c + 4.0
        s = 0 if l == 0 or l == 1 else (mx - l) / min(l, 1 - l)
        h *= 60.0
        if s == 0:
            h = alg.NaN

    return [util.constrain_hue(h), s, l]


def hsl_to_srgb(hsl: Vector) -> Vector:
    """
    HSL to RGB.

    https://en.wikipedia.org/wiki/HSL_and_HSV#HSL_to_RGB_alternative
    """

    h, s, l = hsl
    h = h % 360

    def f(n: int) -> float:
        """Calculate the channels."""
        k = (n + h / 30) % 12
        a = s * min(l, 1 - l)
        return l - a * max(-1, min(k - 3, 9 - k, 1))

    return [f(0), f(8), f(4)]


class HSL(Cylindrical, Space):
    """HSL class."""

    BASE = "srgb"
    NAME = "hsl"
    SERIALIZE = ("--hsl",)
    CHANNELS = (
        Channel("h", 0.0, 360.0, bound=True, flags=FLG_ANGLE),
        Channel("s", 0.0, 1.0, bound=True, flags=FLG_PERCENT),
        Channel("l", 0.0, 1.0, bound=True, flags=FLG_PERCENT)
    )
    CHANNEL_ALIASES = {
        "hue": "h",
        "saturation": "s",
        "lightness": "l"
    }
    WHITE = WHITES['2deg']['D65']
    GAMUT_CHECK = "srgb"

    @classmethod
    def normalize(cls, coords: Vector) -> Vector:
        """On color update."""

        coords = alg.no_nans(coords)
        if coords[1] == 0 or coords[2] in (0, 1):
            coords[0] = alg.NaN

        return coords

    @classmethod
    def to_base(cls, coords: Vector) -> Vector:
        """To sRGB from HSL."""

        return hsl_to_srgb(coords)

    @classmethod
    def from_base(cls, coords: Vector) -> Vector:
        """From sRGB to HSL."""

        return srgb_to_hsl(coords)
