"""
Delta E ITP.

https://kb.portrait.com/help/ictcp-color-difference-metric
"""
from ..distance import DeltaE
import math
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color


class DEITP(DeltaE):
    """Delta E ITP class."""

    NAME = "itp"

    def __init__(self, scalar: float = 720) -> None:
        """Initialize."""

        self.scalar = scalar

    def distance(self, color: 'Color', sample: 'Color', scalar: Optional[float] = None, **kwargs: Any) -> float:
        """Delta E ITP color distance formula."""

        if scalar is None:
            scalar = self.scalar

        i1, t1, p1 = color.convert('ictcp').coords(nans=False)
        i2, t2, p2 = sample.convert('ictcp').coords(nans=False)

        # Equation (1)
        return scalar * math.sqrt((i1 - i2) ** 2 + 0.25 * (t1 - t2) ** 2 + (p1 - p2) ** 2)
