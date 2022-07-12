"""
The xyY color space.

https://en.wikipedia.org/wiki/CIE_1931_color_space#CIE_xy_chromaticity_diagram_and_the_CIE_xyY_color_space
"""
from ..spaces import Space
from ..channels import Channel
from ..cat import WHITES
from .. import util
from ..types import Vector
from typing import Tuple


class XyY(Space):
    """The xyY class."""

    BASE = "xyz-d65"
    NAME = "xyy"
    SERIALIZE = ("--xyy",)  # type: Tuple[str, ...]
    CHANNELS = (
        Channel("x", 0.0, 1.0),
        Channel("y", 0.0, 1.0),
        Channel("Y", 0.0, 1.0)
    )
    WHITE = WHITES['2deg']['D65']

    @classmethod
    def to_base(cls, coords: Vector) -> Vector:
        """To XYZ."""

        return util.xy_to_xyz(coords[0:2], coords[2])

    @classmethod
    def from_base(cls, coords: Vector) -> Vector:
        """From XYZ."""

        return util.xyz_to_xyY(coords, cls.white())
