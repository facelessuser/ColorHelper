"""HSL class."""
from .. import hsl as base
from ...css import parse
from ...css import serialize
from ...types import Vector
from typing import Union, Optional, Tuple, Any, TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover
    from ...color import Color


class HSL(base.HSL):
    """HSL class."""

    def to_string(
        self,
        parent: 'Color',
        *,
        alpha: Optional[bool] = None,
        precision: Optional[int] = None,
        fit: Union[str, bool] = True,
        none: bool = False,
        color: bool = False,
        percent: Union[bool, Sequence] = None,
        comma: bool = False,
        **kwargs: Any
    ) -> str:
        """Convert to CSS."""

        if percent is None:
            if not color:
                percent = True
            else:
                percent = False
        elif isinstance(percent, bool):
            if comma:
                percent = True
        elif comma:
            percent = [False, True, True] + list(percent[3:4])

        return serialize.serialize_css(
            parent,
            func='hsl',
            alpha=alpha,
            precision=precision,
            fit=fit,
            none=none,
            color=color,
            legacy=comma,
            percent=percent,
            scale=100
        )

    def match(
        self,
        string: str,
        start: int = 0,
        fullmatch: bool = True
    ) -> Optional[Tuple[Tuple[Vector, float], int]]:
        """Match a CSS color string."""

        return parse.parse_css(self, string, start, fullmatch)
