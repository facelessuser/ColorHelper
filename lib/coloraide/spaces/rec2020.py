"""Rec 2020 color class."""
from ..cat import WHITES
from .srgb import SRGB
import math
from .. import algebra as alg
from ..types import Vector

ALPHA = 1.09929682680944
BETA = 0.018053968510807
BETA45 = 0.018053968510807 * 4.5


def lin_2020(rgb: Vector) -> Vector:
    """
    Convert an array of rec-2020 RGB values in the range 0.0 - 1.0 to linear light (un-corrected) form.

    https://en.wikipedia.org/wiki/Rec._2020#Transfer_characteristics
    """

    result = []
    for i in rgb:
        # Mirror linear nature of algorithm on the negative axis
        abs_i = abs(i)
        if abs_i < BETA45:
            result.append(i / 4.5)
        else:
            result.append(math.copysign(alg.nth_root((abs_i + ALPHA - 1) / ALPHA, 0.45), i))
    return result


def gam_2020(rgb: Vector) -> Vector:
    """
    Convert an array of linear-light rec-2020 RGB  in the range 0.0-1.0 to gamma corrected form.

    https://en.wikipedia.org/wiki/Rec._2020#Transfer_characteristics
    """

    result = []
    for i in rgb:
        # Mirror linear nature of algorithm on the negative axis
        abs_i = abs(i)
        if abs_i < BETA:
            result.append(4.5 * i)
        else:
            result.append(math.copysign(ALPHA * (abs_i ** 0.45) - (ALPHA - 1), i))
    return result


class Rec2020(SRGB):
    """Rec 2020 class."""

    BASE = "rec2020-linear"
    NAME = "rec2020"
    WHITE = WHITES['2deg']['D65']

    @classmethod
    def to_base(cls, coords: Vector) -> Vector:
        """To XYZ from Rec 2020."""

        return lin_2020(coords)

    @classmethod
    def from_base(cls, coords: Vector) -> Vector:
        """From XYZ to Rec 2020."""

        return gam_2020(coords)
