"""
Catmull-Rom interpolation.

http://www2.cs.uregina.ca/~anima/408/Notes/Interpolation/Parameterized-Curves-Summary.htm
"""
from .bspline import InterpolatorBSpline
from ..interpolate import Interpolator, Interpolate
from .. import algebra as alg
from ..types import Vector
from typing import Optional, Callable, Mapping, List, Union, Sequence, Dict, Any, Type, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color


class InterpolatorCatmullRom(InterpolatorBSpline):
    """Interpolate with Catmull-Rom spline."""

    def setup(self) -> None:
        """Setup."""

        super().setup()
        self.spline = alg.catrom


class CatmullRom(Interpolate):
    """Catmull-Rom interpolation plugin."""

    NAME = "catrom"

    def interpolator(
        self,
        coordinates: List[Vector],
        channel_names: Sequence[str],
        create: Type['Color'],
        easings: List[Optional[Callable[..., float]]],
        stops: Dict[int, float],
        space: str,
        out_space: str,
        progress: Optional[Union[Mapping[str, Callable[..., float]], Callable[..., float]]],
        premultiplied: bool,
        extrapolate: bool = False,
        domain: Optional[List[float]] = None,
        **kwargs: Any
    ) -> Interpolator:
        """Return the Catmull-Rom interpolator."""

        return InterpolatorCatmullRom(
            coordinates,
            channel_names,
            create,
            easings,
            stops,
            space,
            out_space,
            progress,
            premultiplied,
            extrapolate,
            domain
        )
