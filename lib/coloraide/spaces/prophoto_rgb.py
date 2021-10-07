"""Pro Photo RGB color class."""
from ..spaces import RE_DEFAULT_MATCH
from .srgb.base import SRGB
from .xyz import XYZ
from .. import util
import re

ET = 1 / 512
ET2 = 16 / 512

RGB_TO_XYZ = [
    [7.9776048967230273e-01, 1.3518583717574034e-01, 3.1349349581524806e-02],
    [2.8807112822929343e-01, 7.1184321781010151e-01, 8.5653960605259035e-05],
    [0.0000000000000000e+00, 0.0000000000000000e+00, 8.2510460251046025e-01]
]

XYZ_TO_RGB = [
    [1.345798973102828, -0.2555801000799754, -0.05110628506753401],
    [-0.5446224939028346, 1.508232741313278, 0.020536032391479723],
    [0.0, 0.0, 1.2119675456389452]
]


def lin_prophoto_to_xyz(rgb):
    """
    Convert an array of linear-light prophoto-rgb values to CIE XYZ using  D50.D50.

    (so no chromatic adaptation needed afterwards)
    http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html
    """

    return util.dot(RGB_TO_XYZ, rgb)


def xyz_to_lin_prophoto(xyz):
    """Convert XYZ to linear-light prophoto-rgb."""

    return util.dot(XYZ_TO_RGB, xyz)


def lin_prophoto(rgb):
    """
    Convert an array of prophoto-rgb values in the range 0.0 - 1.0 to linear light (un-corrected) form.

    Transfer curve is gamma 1.8 with a small linear portion.

    https://en.wikipedia.org/wiki/ProPhoto_RGB_color_space
    """

    result = []
    for i in rgb:
        # Mirror linear nature of algorithm on the negative axis
        if abs(i) < ET2:
            result.append(i / 16.0)
        else:
            result.append(util.npow(i, 1.8))
    return result


def gam_prophoto(rgb):
    """
    Convert an array of linear-light prophoto-rgb  in the range 0.0-1.0 to gamma corrected form.

    Transfer curve is gamma 1.8 with a small linear portion.

    https://en.wikipedia.org/wiki/ProPhoto_RGB_color_space
    """

    result = []
    for i in rgb:
        # Mirror linear nature of algorithm on the negative axis
        if abs(i) < ET:
            result.append(16.0 * i)
        else:
            result.append(util.nth_root(i, 1.8))
    return result


class ProPhotoRGB(SRGB):
    """Pro Photo RGB class."""

    SPACE = "prophoto-rgb"
    DEFAULT_MATCH = re.compile(RE_DEFAULT_MATCH.format(color_space=SPACE, channels=3))
    WHITE = "D50"

    @classmethod
    def _to_xyz(cls, parent, rgb):
        """To XYZ."""

        return parent.chromatic_adaptation(cls.WHITE, XYZ.WHITE, lin_prophoto_to_xyz(lin_prophoto(rgb)))

    @classmethod
    def _from_xyz(cls, parent, xyz):
        """From XYZ."""

        return gam_prophoto(xyz_to_lin_prophoto(parent.chromatic_adaptation(XYZ.WHITE, cls.WHITE, xyz)))
