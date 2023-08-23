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
from .achromatic import Achromatic as _Achromatic
from ..cat import WHITES
from ..channels import Channel, FLG_MIRROR_PERCENT
from .. import util
from .. import algebra as alg
from .lch import lab_to_lch
from .srgb_linear import lin_srgb_to_xyz
from .srgb import lin_srgb
from ..types import Vector
from typing import Any, List
import math

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
    [0.35031676209499907, 0.7264811939316552, -0.06538442294808501],
    [-0.09098281098284755, -0.31272829052307394, 1.5227665613052603]
]

# LMS to Izazbz matrices
lms_p_to_izazbz_m = [
    [0.5, 0.5, 0],
    [3.524, -4.066708, 0.542708],
    [0.199076, 1.096799, -1.295875]
]

izazbz_to_lms_p_mi = [
    [1.0, 0.13860504327153927, 0.05804731615611883],
    [1.0, -0.1386050432715393, -0.058047316156118904],
    [1.0, -0.09601924202631895, -0.811891896056039]
]

ACHROMATIC_RESPONSE = [
    [0.0009185262133445958, 2.840443191466584e-06, 216.0885802021336],
    [0.0032449260086909186, 8.875176418290735e-06, 216.0865538095895],
    [0.007045724283550615, 1.742628198531671e-05, 216.08513073729978],
    [0.009865500056099596, 2.317265885648471e-05, 216.08447255685712],
    [0.012214842923826377, 2.768276363465363e-05, 216.0840428784794],
    [0.014313828964294468, 3.15364404794859e-05, 216.08371809158197],
    [0.016438077905865333, 3.5290049847676045e-05, 216.08343078937077],
    [0.018605469297130712, 3.898508192957335e-05, 216.08317068540933],
    [0.02080811172991238, 4.261478385537034e-05, 216.0829334034566],
    [0.02303956968571666, 4.617490464976015e-05, 216.0827155404453],
    [0.02529454916234039, 4.966297634911679e-05, 216.0825143871757],
    [0.027568661881969103, 5.307781011104134e-05, 216.08232775391835],
    [0.029858245862958505, 5.641913782115498e-05, 216.08215383175184],
    [0.032160227098370596, 5.9687353969353895e-05, 216.0819911399305],
    [0.03447201166859765, 6.288332788976944e-05, 216.08183842876093],
    [0.03679140069552315, 6.600826589362147e-05, 216.08169464885202],
    [0.03911652265347357, 6.906360946484213e-05, 216.0815588821907],
    [0.04144577901905777, 7.20509595041043e-05, 216.08143037308045],
    [0.04377780027866024, 7.497201997536904e-05, 216.0813084440367],
    [0.046111410055380574, 7.78285557456021e-05, 216.08119250961198],
    [0.04844559565682705, 8.062236105672717e-05, 216.08108206116256],
    [0.050779483741710464, 8.335523609797642e-05, 216.08097664284261],
    [0.053112320097915965, 8.602896956101964e-05, 216.0808758658446],
    [0.05544345274603036, 8.864532585124454e-05, 216.08077937053],
    [0.05777231775004377, 9.120603576758393e-05, 216.08068683882303],
    [0.060098427245276025, 9.371278988327557e-05, 216.08059799668482],
    [0.062421359292580254, 9.616723398809035e-05, 216.08051257202447],
    [0.07282655496930118, 0.00010660656866708172, 216.08016488545363],
    [0.09108704537148082, 0.00012302746725157782, 216.07966036150265],
    [0.10900798276245852, 0.00013720664366179703, 216.0792568965177],
    [0.12658714074774824, 0.00014958895848933898, 216.0789232434426],
    [0.1438408486329413, 0.00016050730576011498, 216.07864044077417],
    [0.16079190286441, 0.00017021501266814123, 216.07839616904852],
    [0.17746453522326563, 0.0001789083001012923, 216.07818199543323],
    [0.1938822908546569, 0.00018674170523656867, 216.07799190659145],
    [0.21006717973109132, 0.00019383878540645526, 216.07782150011536],
    [0.22603940395038172, 0.00020029967178728176, 216.0776674210859],
    [0.24181734649813305, 0.0002062064957239789, 216.0775271074707],
    [0.25741767436011453, 0.00021162735571841754, 216.0773985097046],
    [0.27285548569428925, 0.00021661926443777217, 216.07728001861],
    [0.28814446743495276, 0.00022123037188011426, 216.07717029782012],
    [0.3032970476681226, 0.00022550166532677018, 216.07706827050953],
    [0.318324536052124, 0.00022946828610769828, 216.07697303732877],
    [0.3332372500029604, 0.00023316056105526304, 216.07688383235663],
    [0.34804462653287077, 0.00023660481904069536, 216.0768000283236],
    [0.3627553206321442, 0.00023982404450001245, 216.07672106548637],
    [0.37737729148697624, 0.0002428384038912725, 216.07664646902424],
    [0.3919178779258038, 0.0002456656744964799, 216.07657583096483],
    [0.40638386443891256, 0.00024832159559521613, 216.07650879846213],
    [0.420781539003173, 0.0002508201586917396, 216.07644505801895],
    [0.4351167438075533, 0.0002531738482749366, 216.07638435201847],
    [0.44939491983780117, 0.0002553938438855013, 216.0763264167306],
    [0.46362114614988975, 0.00025749018901337296, 216.076271046612],
    [0.47780017454650436, 0.000259471935031054, 216.0762180267072],
    [0.49193646026919147, 0.0002613472624003357, 216.07616722683406],
    [0.506034189231372, 0.0002631235853618668, 216.07611845640926],
    [0.520097302241697, 0.0002648076406577341, 216.07607158130352],
    [0.5341295166035784, 0.0002664055645672449, 216.07602649958457],
    [0.5481343454215033, 0.0002679229595196272, 216.07598307638068],
    [0.562115114898706, 0.00026936495156998765, 216.0759412038042],
    [0.5760749798710889, 0.00027073624083088496, 216.0759007944157],
    [0.5900169377887273, 0.0002720411453401863, 216.07586174613544],
    [0.6039438413278134, 0.00027328363966826354, 216.07582400851473],
    [0.6178584097918066, 0.0002744673887323733, 216.07578748393507],
    [0.6317632394388409, 0.0002755957777534978, 216.07575212814703],
    [0.6456608128558685, 0.00027667193897750657, 216.07571787420144],
    [0.6595535074843613, 0.0002776987749361305, 216.0756845900282],
    [0.6734436033881548, 0.00027867897881155425, 216.0756523336041],
    [0.6873332903451649, 0.0002796150541276385, 216.07562100643182],
    [0.7012246743322099, 0.0002805093307679912, 216.07559056780278],
    [0.7151197834661946, 0.00028136397973813873, 216.07556096861626],
    [0.7290205734555001, 0.00028218102717968054, 216.07553214064387],
    [0.7429289326111091, 0.00028296236534187003, 216.07550410795596],
    [0.7568466864597538, 0.0002837097645372413, 216.07547681413567],
    [0.7707756019973733, 0.00028442488261536087, 216.0754501913429],
    [0.7847173916174169, 0.0002851092732967129, 216.07542424437477],
    [0.7986737167436694, 0.0002857643945778034, 216.07539893412002],
    [0.8126461911946142, 0.0002863916163923197, 216.07537422001636],
    [0.82663638430444, 0.0002869922264017996, 216.07535011510663],
    [0.8406458238212122, 0.00028756743686351684, 216.07532657427606],
    [0.8546759986026592, 0.0002881183896480139, 216.07530355785332],
    [0.8687283611263583, 0.00028864616127277436, 216.07528106686505],
    [0.8828043298308796, 0.0002891517676790176, 216.0752590661328],
    [0.8969052913010638, 0.0002896361684484102, 216.07523755309595],
    [0.9110326023119082, 0.0002901002704615418, 216.07521649953736],
    [0.9251875917408455, 0.0002905449316470965, 216.07519588476185],
    [0.939371562360337, 0.00029097096413252364, 216.0751757112678],
    [0.9535857925200474, 0.0002913791373231644, 216.07515593963097],
    [0.9678315377267531, 0.000291770180656392, 216.0751365593372]
]  # type: List[Vector]


class Achromatic(_Achromatic):
    """Test if color is achromatic."""

    def convert(self, coords: Vector, **kwargs: Any) -> Vector:
        """Convert to the target color space."""

        return lab_to_lch(xyz_d65_to_jzazbz(lin_srgb_to_xyz(lin_srgb(coords))))


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
    return util.absxyz_to_xyz([xa, ya, za])


def xyz_d65_to_jzazbz(xyzd65: Vector) -> Vector:
    """From XYZ to Jzazbz."""

    # Convert from XYZ D65 to an absolute XYZ D5
    xa, ya, za = util.xyz_to_absxyz(xyzd65)
    xm = (B * xa) - ((B - 1) * za)
    ym = (G * ya) - ((G - 1) * xa)

    # Convert to LMS
    lms = alg.dot(xyz_to_lms_m, [xm, ym, za], dims=alg.D2_D1)

    # PQ encode the LMS
    pqlms = util.pq_st2084_oetf(lms, m2=M2)

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
        Channel("jz", 0.0, 1.0, limit=(0.0, None)),
        Channel("az", -0.5, 0.5, flags=FLG_MIRROR_PERCENT),
        Channel("bz", -0.5, 0.5, flags=FLG_MIRROR_PERCENT)
    )
    CHANNEL_ALIASES = {
        "lightness": 'jz',
        "a": 'az',
        "b": 'bz'
    }
    WHITE = WHITES['2deg']['D65']
    DYNAMIC_RANGE = 'hdr'
    # Precalculated from
    # [
    #     (1, 5, 5, 1000.0),
    #     (1, 52, 2, 200.0),
    #     (30, 521, 8, 100.0)
    # ]
    ACHROMATIC = Achromatic(
        ACHROMATIC_RESPONSE,
        2.121e-7,
        9.863e-7,
        0.00039,
        'catrom',
    )

    def resolve_channel(self, index: int, coords: Vector) -> float:
        """Resolve channels."""

        if index in (1, 2):
            if not math.isnan(coords[index]):
                return coords[index]

            return self.ACHROMATIC.get_ideal_ab(coords[0])[index - 1]

        value = coords[index]
        return self.channels[index].nans if math.isnan(value) else value

    def is_achromatic(self, coords: Vector) -> bool:
        """Check if color is achromatic."""

        c, h = alg.rect_to_polar(coords[1], coords[2])
        return coords[0] == 0.0 or self.ACHROMATIC.test(coords[0], c, h)

    def to_base(self, coords: Vector) -> Vector:
        """To XYZ from Jzazbz."""

        return jzazbz_to_xyz_d65(coords)

    def from_base(self, coords: Vector) -> Vector:
        """From XYZ to Jzazbz."""

        return xyz_d65_to_jzazbz(coords)
