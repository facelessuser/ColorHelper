"""XYZ D65 class."""
import math
from ..spaces import Space, RGBish
from ..cat import WHITES
from ..channels import Channel
from .. import util
from .. import algebra as alg
from ..types import Vector
from typing import Tuple


class XYZD65(RGBish, Space):
    """XYZ D65 class."""

    BASE = "xyz-d65"
    NAME = "xyz-d65"
    SERIALIZE = ("xyz-d65", 'xyz')  # type: Tuple[str, ...]
    CHANNELS = (
        Channel("x", 0.0, 1.0),
        Channel("y", 0.0, 1.0),
        Channel("z", 0.0, 1.0)
    )
    WHITE = WHITES['2deg']['D65']

    def is_achromatic(self, coords: Vector) -> bool:
        """Is achromatic."""

        for x in alg.vcross(coords, util.xy_to_xyz(self.white())):
            if not alg.isclose(0.0, x, abs_tol=1e-5, dims=alg.SC):
                return False
        return True

    def to_base(self, coords: Vector) -> Vector:
        """
        To XYZ (no change).

        Any needed chromatic adaptation is handled in the parent Color object.
        """

        return coords

    def from_base(self, coords: Vector) -> Vector:
        """
        From XYZ (no change).

        Any needed chromatic adaptation is handled in the parent Color object.
        """

        return coords
