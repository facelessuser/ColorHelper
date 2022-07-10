"""
CIE 1960 UCS color class.

http://en.wikipedia.org/wiki/CIE_1960_color_space#Relation_to_CIE_XYZ
"""
from ...coloraide.spaces import Space
from ...coloraide.channels import Channel
from ...coloraide.cat import WHITES
from ...coloraide.types import Vector
from typing import Tuple


def xyz_to_ucs(xyz: Vector) -> Vector:
    """Translate XYZ to 1960 UCS."""

    x, y, z = xyz
    return [(2 / 3) * x, y, (-x + 3 * y + z) * 0.5]


def ucs_to_xyz(ucs: Vector) -> Vector:
    """Translate 1960 UCS to XYZ."""

    u, v, w = ucs
    return [(3 / 2) * u, v, (3 / 2) * u - 3 * v + 2 * w]


class UCS(Space):
    """The 1960 UCS class."""

    BASE = "xyz-d65"
    NAME = "ucs"
    SERIALIZE = ("--ucs",)  # type: Tuple[str, ...]
    CHANNELS = (
        Channel("u", 0.0, 1.0),
        Channel("v", 0.0, 1.0),
        Channel("w", 0.0, 1.0)
    )
    WHITE = WHITES['2deg']['D65']

    @classmethod
    def to_base(cls, coords: Vector) -> Vector:
        """To XYZ."""

        return ucs_to_xyz(coords)

    @classmethod
    def from_base(cls, coords: Vector) -> Vector:
        """From XYZ."""

        return xyz_to_ucs(coords)
