"""
Prismatic color space.

Creates a Maxwell color triangle with a lightness component.

http://psgraphics.blogspot.com/2015/10/prismatic-color-model.html
https://studylib.net/doc/14656976/the-prismatic-color-space-for-rgb-computations
"""
from ..spaces import Space
from ..channels import Channel
from ..cat import WHITES
from ..types import Vector
from typing import Tuple


def srgb_to_lrgb(rgb: Vector) -> Vector:
    """Convert sRGB to Prismatic."""

    l = max(rgb)
    s = sum(rgb)
    return [l] + ([(c / s) for c in rgb] if s != 0 else [0, 0, 0])


def lrgb_to_srgb(lrgb: Vector) -> Vector:
    """Convert Prismatic to sRGB."""

    rgb = lrgb[1:]
    l = lrgb[0]
    mx = max(rgb)
    return [(l * c) / mx for c in rgb] if mx != 0 else [0, 0, 0]


class Prismatic(Space):
    """The Prismatic color class."""

    BASE = "srgb"
    NAME = "prismatic"
    SERIALIZE = ("--prismatic",)  # type: Tuple[str, ...]
    EXTENDED_RANGE = False
    CHANNELS = (
        Channel("l", 0.0, 1.0, bound=True),
        Channel("r", 0.0, 1.0, bound=True),
        Channel("g", 0.0, 1.0, bound=True),
        Channel("b", 0.0, 1.0, bound=True)
    )
    CHANNEL_ALIASES = {
        "lightness": 'l',
        "red": 'r',
        "green": 'g',
        "blue": 'b'
    }
    WHITE = WHITES['2deg']['D65']

    @classmethod
    def to_base(cls, coords: Vector) -> Vector:
        """To sRGB."""

        return lrgb_to_srgb(coords)

    @classmethod
    def from_base(cls, coords: Vector) -> Vector:
        """From sRGB."""

        return srgb_to_lrgb(coords)
