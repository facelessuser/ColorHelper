"""Oklab class."""
from .. import oklab as base
from ...css import parse
from ...css import serialize
from ...types import Vector
from typing import Union, Optional, Tuple, Any, TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover
    from ...color import Color


class Oklab(base.Oklab):
    """Oklab class."""

    def to_string(
        self,
        parent: 'Color',
        *,
        alpha: Optional[bool] = None,
        precision: Optional[int] = None,
        fit: Union[str, bool] = True,
        none: bool = False,
        color: bool = False,
        percent: Union[bool, Sequence] = False,
        **kwargs: Any
    ) -> str:
        """Convert to CSS."""

        return serialize.serialize_css(
            parent,
            func='oklab',
            alpha=alpha,
            precision=precision,
            fit=fit,
            none=none,
            color=color,
            percent=percent
        )

    def match(
        self,
        string: str,
        start: int = 0,
        fullmatch: bool = True
    ) -> Optional[Tuple[Tuple[Vector, float], int]]:
        """Match a CSS color string."""

        return parse.parse_css(self, string, start, fullmatch)
