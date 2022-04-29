"""
Delta E ITP.

https://kb.portrait.com/help/ictcp-color-difference-metric
"""
from ..distance import DeltaE
import math
from .. import algebra as alg
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color


class DEITP(DeltaE):
    """Delta E ITP class."""

    NAME = "itp"

    @classmethod
    def distance(cls, color: 'Color', sample: 'Color', scalar: float = 720, **kwargs: Any) -> float:
        """Delta E ITP color distance formula."""

        i1, t1, p1 = alg.no_nans(color.convert('ictcp')[:-1])
        i2, t2, p2 = alg.no_nans(sample.convert('ictcp')[:-1])

        # Equation (1)
        return scalar * math.sqrt((i1 - i2) ** 2 + 0.25 * (t1 - t2) ** 2 + (p1 - p2) ** 2)
