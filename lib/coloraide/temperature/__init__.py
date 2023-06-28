"""Temperature plugin."""
from abc import ABCMeta, abstractmethod
from ..types import Plugin, Vector
from typing import TYPE_CHECKING, Union, Optional, Any, Type

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color


class CCT(Plugin, metaclass=ABCMeta):
    """Delta E plugin class."""

    NAME = ''

    @abstractmethod
    def to_cct(self, color: 'Color', **kwargs: Any) -> Vector:
        """Calculate a color's CCT."""

    @abstractmethod
    def from_cct(
        self,
        color: Type['Color'],
        space: str,
        kelvin: float,
        duv: float,
        scale: bool,
        scale_space: Optional[str],
        **kwargs: Any
    ) -> 'Color':
        """Calculate a color that satisfies the CCT."""


def cct(name: Optional[str], color: Union[Type['Color'], 'Color']) -> CCT:
    """Get the appropriate contrast plugin."""

    if name is None:
        name = color.CCT

    method = color.CCT_MAP.get(name)
    if not method:
        raise ValueError("'{}' CCT method is not supported".format(name))

    return method
