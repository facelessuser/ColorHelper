"""sRGB Linear color class."""
from ..cat import WHITES
from .srgb import sRGB
from .. import algebra as alg
from ..types import Vector


RGB_TO_XYZ = [
    [0.4123907992659593, 0.357584339383878, 0.1804807884018343],
    [0.21263900587151024, 0.715168678767756, 0.07219231536073371],
    [0.01933081871559182, 0.11919477979462598, 0.9505321522496607]
]

XYZ_TO_RGB = [
    [3.240969941904523, -1.5373831775700941, -0.4986107602930035],
    [-0.9692436362808797, 1.8759675015077204, 0.04155505740717562],
    [0.05563007969699365, -0.20397695888897652, 1.0569715142428784]
]


def lin_srgb_to_xyz(rgb: Vector) -> Vector:
    """
    Convert an array of linear-light sRGB values to CIE XYZ using sRGB's own white.

    D65 (no chromatic adaptation)
    """

    return alg.matmul(RGB_TO_XYZ, rgb, dims=alg.D2_D1)


def xyz_to_lin_srgb(xyz: Vector) -> Vector:
    """Convert XYZ to linear-light sRGB."""

    return alg.matmul(XYZ_TO_RGB, xyz, dims=alg.D2_D1)


class sRGBLinear(sRGB):
    """sRGB linear."""

    BASE = 'xyz-d65'
    NAME = "srgb-linear"
    SERIALIZE = ("srgb-linear",)
    WHITE = WHITES['2deg']['D65']

    def to_base(self, coords: Vector) -> Vector:
        """To XYZ from sRGB Linear."""

        return lin_srgb_to_xyz(coords)

    def from_base(self, coords: Vector) -> Vector:
        """From XYZ to sRGB Linear."""

        return xyz_to_lin_srgb(coords)
