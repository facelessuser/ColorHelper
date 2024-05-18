"""
Delta E CAM16.

https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9698626/pdf/sensors-22-08869.pdf
"""
from __future__ import annotations
import math
from ..distance import DeltaE
from ..deprecate import warn_deprecated
from typing import Any, TYPE_CHECKING
from ..spaces.cam16_ucs import COEFFICENTS, CAM16UCS

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color


WARN_MSG = (
    "The 'model' parameter is now deprecated, please specify the CAM16 UCS/LCD/SCD space name via 'space' instead"
)


class DECAM16(DeltaE):
    """Delta E CAM16 class."""

    NAME = "cam16"

    def distance(
        self,
        color: Color,
        sample: Color,
        space: str = "cam16-ucs",
        model: str | None = None,
        **kwargs: Any
    ) -> float:
        """Delta E CAM16 color distance formula."""

        # Legacy approach to specifying CAM16 approach
        if model is not None:  # pragma: no cover
            warn_deprecated(WARN_MSG)
            space = 'cam16-{}'.format(model)
            kl = COEFFICENTS[model][0]

        # Normal approach to specifying CAM16 target space
        else:
            cs = color.CS_MAP[space]
            if not isinstance(color.CS_MAP[space], CAM16UCS):
                raise ValueError("Distance color space must be derived from CAM16UCS.")
            model = cs.MODEL  # type: ignore[attr-defined]
            kl = COEFFICENTS[model][0]

        j1, a1, b1 = color.convert(space).coords(nans=False)
        j2, a2, b2 = sample.convert(space).coords(nans=False)

        dj = j1 - j2
        da = a1 - a2
        db = b1 - b2

        return math.sqrt((dj / kl) ** 2 + da ** 2 + db ** 2)
