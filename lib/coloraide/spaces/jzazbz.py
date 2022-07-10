"""
Jzazbz class.

https://www.osapublishing.org/oe/fulltext.cfm?uri=oe-25-13-15131&id=368272

There seems to be some debate on how to scale Jzazbz. Colour Science chooses not to scale at all.
Colorio seems to scale at 100.

The spec mentions multiple times targeting a luminance of 10,000 cd/m^2.
Relative XYZ has Y=1 for media white
BT.2048 says media white Y=203 at PQ 58
This is confirmed here: https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-BT.2408-3-2019-PDF-E.pdf

It is tough to tell who is correct as everything passes through the MATLAB scripts fine as it
just scales the results differently, so forward and backwards translation comes out great regardless,
but looking at the images in the spec, it seems the scaling using Y=203 at PQ 58 may be correct. It
is almost certain that some scaling is being applied and that applying none is almost certainly wrong.

If at some time that these assumptions are incorrect, we will be happy to alter the model.
"""
from ..spaces import Space, Labish
from ..cat import WHITES
from ..channels import Channel, FLG_MIRROR_PERCENT
from .. import util
from .. import algebra as alg
from ..types import Vector

B = 1.15
G = 0.66
D = -0.56
D0 = 1.6295499532821566E-11

# All PQ Values are equivalent to defaults as stated in link below except `M2` (and `IM2`):
# https://en.wikipedia.org/wiki/High-dynamic-range_video#Perceptual_quantizer
#
# ```
# M1 = 2610 / (2 ** 14)
# IM1 = (2 ** 14) / 2610
# C1 = 3424 / (2 ** 12)
# C2 = 2413 / (2 ** 7)
# C3 = 2392 / (2 ** 7)
# M2 = 1.7 * 2523 / (2 ** 5)
# IM2 = (2 ** 5) / (1.7 * 2523)
# ```
M2 = 1.7 * 2523 / (2 ** 5)


# XYZ transform matrices
xyz_to_lms_m = [
    [0.41478972, 0.579999, 0.014648],
    [-0.20151, 1.120649, 0.0531008],
    [-0.0166008, 0.2648, 0.6684799]
]

lms_to_xyz_mi = [
    [1.9242264357876069, -1.0047923125953657, 0.037651404030617994],
    [0.350316762094999, 0.7264811939316552, -0.06538442294808501],
    [-0.09098281098284752, -0.3127282905230739, 1.5227665613052603]
]

# LMS to Izazbz matrices
lms_p_to_izazbz_m = [
    [0.5, 0.5, 0],
    [3.524, -4.066708, 0.542708],
    [0.199076, 1.096799, -1.295875]
]

izazbz_to_lms_p_mi = [
    [1.0, 0.1386050432715393, 0.05804731615611886],
    [1.0, -0.1386050432715393, -0.05804731615611886],
    [0.9999999999999998, -0.09601924202631895, -0.8118918960560388]
]


def jzazbz_to_xyz_d65(jzazbz: Vector) -> Vector:
    """From Jzazbz to XYZ."""

    jz, az, bz = jzazbz

    # Calculate Iz
    iz = (jz + D0) / (1 + D - D * (jz + D0))

    # Convert to LMS prime
    pqlms = alg.dot(izazbz_to_lms_p_mi, [iz, az, bz], dims=alg.D2_D1)

    # Decode PQ LMS to LMS
    lms = util.pq_st2084_eotf(pqlms, m2=M2)

    # Convert back to absolute XYZ D65
    xm, ym, za = alg.dot(lms_to_xyz_mi, lms, dims=alg.D2_D1)
    xa = (xm + ((B - 1) * za)) / B
    ya = (ym + ((G - 1) * xa)) / G

    # Convert back to normal XYZ D65
    return util.absxyzd65_to_xyz_d65([xa, ya, za])


def xyz_d65_to_jzazbz(xyzd65: Vector) -> Vector:
    """From XYZ to Jzazbz."""

    # Convert from XYZ D65 to an absolute XYZ D5
    xa, ya, za = util.xyz_d65_to_absxyzd65(xyzd65)
    xm = (B * xa) - ((B - 1) * za)
    ym = (G * ya) - ((G - 1) * xa)

    # Convert to LMS
    lms = alg.dot(xyz_to_lms_m, [xm, ym, za], dims=alg.D2_D1)

    # PQ encode the LMS
    pqlms = util.pq_st2084_inverse_eotf(lms, m2=M2)

    # Calculate Izazbz
    iz, az, bz = alg.dot(lms_p_to_izazbz_m, pqlms, dims=alg.D2_D1)

    # Calculate Jz
    jz = ((1 + D) * iz) / (1 + (D * iz)) - D0
    return [jz, az, bz]


class Jzazbz(Labish, Space):
    """Jzazbz class."""

    BASE = "xyz-d65"
    NAME = "jzazbz"
    SERIALIZE = ("--jzazbz",)
    CHANNELS = (
        Channel("jz", 0.0, 1.0),
        Channel("az", -0.5, 0.5, flags=FLG_MIRROR_PERCENT),
        Channel("bz", -0.5, 0.5, flags=FLG_MIRROR_PERCENT)
    )
    CHANNEL_ALIASES = {
        "lightness": 'jz',
        "a": 'az',
        "b": 'bz'
    }
    WHITE = WHITES['2deg']['D65']

    @classmethod
    def to_base(cls, coords: Vector) -> Vector:
        """To XYZ from Jzazbz."""

        return jzazbz_to_xyz_d65(coords)

    @classmethod
    def from_base(cls, coords: Vector) -> Vector:
        """From XYZ to Jzazbz."""

        return xyz_d65_to_jzazbz(coords)
