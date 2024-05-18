"""sRGB color class."""
from __future__ import annotations
from .. import srgb as base
from ...css import parse
from ...css import serialize
from typing import Any, Tuple, TYPE_CHECKING, Sequence
from ...types import Vector

if TYPE_CHECKING:  # pragma: no cover
    from ...color import Color


class sRGB(base.sRGB):
    """sRGB class."""

    def to_string(
        self,
        parent: Color,
        *,
        alpha: bool | None = None,
        precision: int | None = None,
        fit: bool | str | dict[str, Any] = True,
        none: bool = False,
        color: bool = False,
        hex: bool = False,  # noqa: A002
        names: bool = False,
        comma: bool = False,
        upper: bool = False,
        percent: bool | Sequence[bool] = False,
        compress: bool = False,
        **kwargs: Any
    ) -> str:
        """Convert to CSS."""

        return serialize.serialize_css(
            parent,
            func='rgb',
            alpha=alpha,
            precision=precision,
            fit=fit,
            none=none,
            color=color,
            hexa=hex,
            name=names,
            legacy=comma,
            upper=upper,
            percent=percent,
            compress=compress,
            scale=255
        )

    def match(
        self,
        string: str,
        start: int = 0,
        fullmatch: bool = True
    ) -> Tuple[Tuple[Vector, float], int] | None:
        """Match a CSS color string."""

        return parse.parse_css(self, string, start, fullmatch)
