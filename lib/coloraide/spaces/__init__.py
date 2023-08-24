"""Color base."""
from abc import ABCMeta, abstractmethod
from ..channels import Channel
from ..css import serialize
from ..deprecate import deprecated
from ..types import VectorLike, Vector, Plugin
from typing import Tuple, Dict, Optional, Union, Any, List, TYPE_CHECKING
import math

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color


class Regular:
    """Regular 3D color space usually with a range between 0 - 1."""


class Cylindrical:
    """Cylindrical space."""

    def hue_name(self) -> str:
        """Hue channel name."""

        return "h"

    def hue_index(self) -> int:  # pragma: no cover
        """Get hue index."""

        return self.get_channel_index(self.hue_name())  # type: ignore[no-any-return, attr-defined]


class RGBish(Regular):
    """RGB-ish space."""

    def names(self) -> Tuple[str, ...]:
        """Return RGB-ish names in order R G B."""

        return self.channels[:-1]  # type: ignore[no-any-return, attr-defined]

    def indexes(self) -> List[int]:
        """Return the index of RGB-ish channels."""

        return [self.get_channel_index(name) for name in self.names()]  # type: ignore[attr-defined]


class HSLish(Cylindrical):
    """HSL-ish space."""

    def names(self) -> Tuple[str, ...]:
        """Return HSL-ish names in order H S L."""

        return self.channels[:-1]  # type: ignore[no-any-return, attr-defined]

    def indexes(self) -> List[int]:
        """Return the index of HSL-ish channels."""

        return [self.get_channel_index(name) for name in self.names()]  # type: ignore[attr-defined]


class HSVish(Cylindrical):
    """HSV-ish space."""

    def names(self) -> Tuple[str, ...]:
        """Return HSV-ish names in order H S V."""

        return self.channels[:-1]  # type: ignore[no-any-return, attr-defined]

    def indexes(self) -> List[int]:
        """Return the index of HSV-ish channels."""

        return [self.get_channel_index(name) for name in self.names()]  # type: ignore[attr-defined]


class HWBish(Cylindrical):
    """HWB-ish space."""

    def names(self) -> Tuple[str, ...]:
        """Return HWB-ish names in order H W B."""

        return self.channels[:-1]  # type: ignore[no-any-return, attr-defined]

    def indexes(self) -> List[int]:
        """Return the index of HWB-ish channels."""

        return [self.get_channel_index(name) for name in self.names()]  # type: ignore[attr-defined]


class Labish:
    """Lab-ish color spaces."""

    @deprecated("Please use 'names' instead.")
    def labish_names(self) -> Tuple[str, ...]:  # pragma: no cover
        """Return Lab-ish names in the order L a b."""

        return self.names()

    @deprecated("Please use 'indexes' instead.")
    def labish_indexes(self) -> List[int]:  # pragma: no cover
        """Return the index of the Lab-ish channels."""

        return self.indexes()

    def names(self) -> Tuple[str, ...]:
        """Return Lab-ish names in the order L a b."""

        return self.channels[:-1]  # type: ignore[no-any-return, attr-defined]

    def labish_indexes(self) -> List[int]:  # pragma: no cover
        """Return the index of the Lab-ish channels."""

        return [self.get_channel_index(name) for name in self.names()]  # type: ignore[attr-defined]


class LChish(Cylindrical):
    """LCh-ish color spaces."""

    @deprecated("Please use 'names' instead.")
    def lchish_names(self) -> Tuple[str, ...]:  # pragma: no cover
        """Return LCh-ish names in the order L c h."""

        return self.names()

    @deprecated("Please use 'indexes' instead.")
    def lchish_indexes(self) -> List[int]:  # pragma: no cover
        """Return the index of the Lab-ish channels."""

        return self.indexes()

    def names(self) -> Tuple[str, ...]:
        """Return LCh-ish names in the order L c h."""

        return self.channels[:-1]  # type: ignore[no-any-return, attr-defined]

    def indexes(self) -> List[int]:
        """Return the index of the Lab-ish channels."""

        return [self.get_channel_index(name) for name in self.names()]  # type: ignore[attr-defined]


alpha_channel = Channel('alpha', 0.0, 1.0, bound=True, limit=(0.0, 1.0))


class SpaceMeta(ABCMeta):
    """Ensure on subclass that the subclass has new instances of mappings."""

    def __init__(cls, name: str, bases: Tuple[object, ...], clsdict: Dict[str, Any]) -> None:
        """Copy mappings on subclass."""

        if len(cls.mro()) > 2:
            cls.CHANNEL_ALIASES = cls.CHANNEL_ALIASES.copy()  # type: Dict[str, str]


class Space(Plugin, metaclass=SpaceMeta):
    """Base color space object."""

    BASE = ""  # type: str
    # Color space name
    NAME = ""
    # Serialized name
    SERIALIZE = ()  # type: Tuple[str, ...]
    # Channel names
    CHANNELS = ()  # type: Tuple[Channel, ...]
    # Channel aliases
    CHANNEL_ALIASES = {}  # type: Dict[str, str]
    # Enable or disable default color format parsing and serialization.
    COLOR_FORMAT = True
    # Should this color also be checked in a different color space? Only when set to a string (specifying a color space)
    # will the default gamut checking also check the specified space as well as the current.
    #
    # Gamut checking:
    #   The specified color space will be checked first followed by the original. Assuming the parent color space fits,
    #   the original should fit as well, but there are some cases when a parent color space that is slightly out of
    #   gamut, when evaluated with a threshold, may appear to be in gamut enough, but when checking the original color
    #   space, the values can be greatly out of specification (looking at you HSL).
    GAMUT_CHECK = None  # type: Optional[str]
    # When set to `True`, this denotes that the color space has the ability to represent out of gamut in colors in an
    # extended range. When interpolation is done, if colors are interpolated in a smaller gamut than the colors being
    # interpolated, the colors will usually be gamut mapped, but if the interpolation space happens to support extended
    # ranges, then the colors will not be gamut mapped even if their gamut is larger than the target interpolation
    # space.
    EXTENDED_RANGE = False
    # White point
    WHITE = (0.0, 0.0)
    # What is the color space's dynamic range
    DYNAMIC_RANGE = 'sdr'

    def __init__(self, **kwargs: Any) -> None:
        """Initialize."""

        self.channels = self.CHANNELS + (alpha_channel,)
        self._color_ids = (self.NAME,) if not self.SERIALIZE else self.SERIALIZE

    def get_channel_index(self, name: str) -> int:
        """Get channel index."""

        return self.channels.index(self.CHANNEL_ALIASES.get(name, name))

    def resolve_channel(self, index: int, coords: Vector) -> float:
        """Resolve channels."""

        value = coords[index]
        return self.channels[index].nans if math.isnan(value) else value

    def _serialize(self) -> Tuple[str, ...]:
        """Get the serialized name."""

        return self._color_ids

    def is_achromatic(self, coords: Vector) -> Optional[bool]:  # pragma: no cover
        """Check if color is achromatic."""

        return None

    @classmethod
    def white(cls) -> VectorLike:
        """Get the white color for this color space."""

        return cls.WHITE

    @abstractmethod
    def to_base(self, coords: Vector) -> Vector:  # pragma: no cover
        """To base color."""

    @abstractmethod
    def from_base(self, coords: Vector) -> Vector:  # pragma: no cover
        """From base color."""

    def to_string(
        self,
        parent: 'Color',
        *,
        alpha: Optional[bool] = None,
        precision: Optional[int] = None,
        fit: Union[bool, str] = True,
        none: bool = False,
        **kwargs: Any
    ) -> str:
        """Convert to CSS 'color' string: `color(space coords+ / alpha)`."""

        return serialize.serialize_css(
            parent,
            color=True,
            alpha=alpha,
            precision=precision,
            fit=fit,
            none=none
        )

    def match(
        self,
        string: str,
        start: int = 0,
        fullmatch: bool = True
    ) -> Optional[Tuple[Tuple[Vector, float], int]]:
        """Match a color by string."""

        return None
