"""Uncalibrated, naive CMY color space."""
from ..spaces import Space
from ..channels import Channel
from ..cat import WHITES
from ..types import Vector
from typing import Tuple


def srgb_to_cmy(rgb: Vector) -> Vector:
    """Convert sRGB to CMY."""

    return [1 - c for c in rgb]


def cmy_to_srgb(cmy: Vector) -> Vector:
    """Convert CMY to sRGB."""

    return [1 - c for c in cmy]


class CMY(Space):
    """The CMY color class."""

    BASE = "srgb"
    NAME = "cmy"
    SERIALIZE = ("--cmy",)  # type: Tuple[str, ...]
    CHANNELS = (
        Channel("c", 0.0, 1.0, bound=True),
        Channel("m", 0.0, 1.0, bound=True),
        Channel("y", 0.0, 1.0, bound=True)
    )
    CHANNEL_ALIASES = {
        "cyan": 'c',
        "magenta": 'm',
        "yellow": 'y'
    }
    WHITE = WHITES['2deg']['D65']

    @classmethod
    def to_base(cls, coords: Vector) -> Vector:
        """To sRGB."""

        return cmy_to_srgb(coords)

    @classmethod
    def from_base(cls, coords: Vector) -> Vector:
        """From sRGB."""

        return srgb_to_cmy(coords)
