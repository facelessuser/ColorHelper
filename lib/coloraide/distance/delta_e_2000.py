"""Delta E 2000."""
from __future__ import annotations
import math
from ..distance import DeltaE
from ..spaces.lab import CIELab
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color


class DE2000(DeltaE):
    """Delta E 2000 class."""

    NAME = "2000"
    G_CONST = 25 ** 7

    def __init__(
        self,
        kl: float = 1,
        kc: float = 1,
        kh: float = 1,
        space: str = 'lab-d65'
    ):
        """Initialize."""

        self.kl = kl
        self.kc = kc
        self.kh = kh
        self.space = space

    def distance(
        self,
        color: Color,
        sample: Color,
        kl: float | None = None,
        kc: float | None = None,
        kh: float | None = None,
        space: str | None = None,
        **kwargs: Any
    ) -> float:
        """
        Calculate distance doing a direct translation of the algorithm from the CIE Delta E 2000 paper.

        We denoted prime (L') with trailing 'p' and mean is represented with a trailing 'm'.
        Delta has a preceding 'd'. I'm not sure I was completely consistent.

        http://www2.ece.rochester.edu/~gsharma/ciede2000/ciede2000noteCRNA.pdf
        """

        if kl is None:
            kl = self.kl

        if kc is None:
            kc = self.kc

        if kh is None:
            kh = self.kh

        if space is None:
            space = self.space
        if not isinstance(color.CS_MAP[space], CIELab):
            raise ValueError("Distance color space must be a CIE Lab color space.")

        l1, a1, b1 = color.convert(space).coords(nans=False)
        l2, a2, b2 = sample.convert(space).coords(nans=False)

        # Equation (2)
        c1 = math.sqrt(a1 ** 2 + b1 ** 2)
        c2 = math.sqrt(a2 ** 2 + b2 ** 2)

        # Equation (3)
        cm = (c1 + c2) / 2

        # Equation (4)
        c7 = cm ** 7
        g = 0.5 * (1 - math.sqrt(c7 / (c7 + self.G_CONST)))

        # Equation (5)
        ap1 = (1 + g) * a1
        ap2 = (1 + g) * a2

        # Equation (6)
        cp1 = math.sqrt(ap1 ** 2 + b1 ** 2)
        cp2 = math.sqrt(ap2 ** 2 + b2 ** 2)

        # Equation (7)
        hp1 = 0 if (ap1 == 0 and b1 == 0) else math.atan2(b1, ap1)
        hp2 = 0 if (ap2 == 0 and b2 == 0) else math.atan2(b2, ap2)
        hp1 = math.degrees(hp1 + math.tau if hp1 < 0.0 else hp1)
        hp2 = math.degrees(hp2 + math.tau if hp2 < 0.0 else hp2)

        # Equation (8)
        dl = l1 - l2

        # Equation (9)
        dc = cp1 - cp2

        # Equation (10)
        hdiff = hp1 - hp2
        if cp1 * cp2 == 0.0:
            dh = 0.0
        elif abs(hdiff) <= 180.0:
            dh = hdiff
        else:
            # If not `hdiff > 180.0` and not `abs(hdiff) <= 180.0`
            # then it must be `hdiff < -180`
            offset = -360 if hdiff > 180.0 else 360
            dh = hdiff + offset

        # Equation (11)
        dh = 2 * math.sqrt(cp2 * cp1) * math.sin(math.radians(dh / 2))

        # Equation (12)
        lpm = (l1 + l2) / 2

        # Equation (13)
        cpm = (cp1 + cp2) / 2

        # Equation (14)
        hsum = hp1 + hp2
        if cp1 * cp2 == 0:
            hpm = hsum
        elif abs(hp1 - hp2) > 180:
            # if not `hsum < 360`
            # then it must be `hsum >= 360`
            offset = 360 if hsum < 360 else -360
            hpm = (hsum + offset) / 2
        else:  # `abs(hp1 - hp2) <= 180`
            hpm = hsum / 2

        # Equation (15)
        t = (
            1 -
            (0.17 * math.cos(math.radians(hpm - 30))) +
            (0.24 * math.cos(math.radians(2 * hpm))) +
            (0.32 * math.cos(math.radians((3 * hpm) + 6))) -
            (0.20 * math.cos(math.radians((4 * hpm) - 63)))
        )

        # Equation (16)
        dt = 30 * math.exp(-1 * ((hpm - 275) / 25) ** 2)

        # Equation (17)
        cpm7 = cpm ** 7
        rc = 2 * math.sqrt(cpm7 / (cpm7 + self.G_CONST))

        # Equation (18)
        l_temp = (lpm - 50) ** 2
        sl = 1 + ((0.015 * l_temp) / math.sqrt(20 + l_temp))

        # Equation (19)
        sc = 1 + 0.045 * cpm

        # Equation (20)
        sh = 1 + 0.015 * cpm * t

        # Equation (21)
        rt = -1 * math.sin(math.radians(2 * dt)) * rc

        # Equation (22)
        return math.sqrt(
            (dl / (kl * sl)) ** 2 +
            (dc / (kc * sc)) ** 2 +
            (dh / (kh * sh)) ** 2 +
            rt * (dc / (kc * sc)) * (dh / (kh * sh))
        )
