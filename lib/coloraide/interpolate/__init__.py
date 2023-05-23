"""
Interpolation methods.

Originally, the base code for `interpolate`, `mix` and `steps` was ported from the
https://colorjs.io project. Since that time, there has been significant modifications
that add additional features etc. The base logic though is attributed to the original
authors.

In general, the logic mimics in many ways the `color-mix` function as outlined in the Level 5
color draft (Oct 2020), but the initial approach was modeled directly off of the work done in
color.js.
---
Original Authors: Lea Verou, Chris Lilley
License: MIT (As noted in https://github.com/LeaVerou/color.js/blob/master/package.json)
"""
import math
import functools
from abc import ABCMeta, abstractmethod
from .. import util
from .. import algebra as alg
from .. spaces import HSVish, HSLish, Cylindrical, RGBish, LChish, Labish
from ..types import Vector, ColorInput, Plugin
from typing import Callable, Dict, Tuple, Optional, Type, Sequence, Union, Mapping, List, Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..color import Color

__all__ = ('stop', 'hint', 'get_interpolator')


class stop:
    """Color stop."""

    __slots__ = ('color', 'stop')

    def __init__(self, color: ColorInput, value: float) -> None:
        """Color stops."""

        self.color = color
        self.stop = value


def midpoint(t: float, h: float = 0.5) -> float:
    """Midpoint easing function."""

    return 0.0 if h <= 0 or h >= 1 else math.pow(t, math.log(0.5) / math.log(h))


def hint(mid: float) -> Callable[..., float]:
    """A generate a midpoint easing function."""

    return functools.partial(midpoint, h=mid)


def normalize_domain(d: List[float]) -> List[float]:
    """Normalize domain between 0 and 1."""

    total = d[-1] - d[0]
    regions = len(d) - 1
    values = [0.0]
    for index in range(regions):
        a, b = d[index:index + 2]
        l = b - a
        values.append(values[-1] + (l / total if total else 0))
    return values


class Interpolator(metaclass=ABCMeta):
    """Interpolator."""

    def __init__(
        self,
        coordinates: List[Vector],
        channel_names: Sequence[str],
        create: Type['Color'],
        easings: List[Optional[Callable[..., float]]],
        stops: Dict[int, float],
        space: str,
        out_space: str,
        progress: Optional[Union[Callable[..., float], Mapping[str, Callable[..., float]]]],
        premultiplied: bool,
        extrapolate: bool = False,
        domain: Optional[List[float]] = None,
        **kwargs: Any
    ):
        """Initialize."""

        self.start = stops[0]
        self.end = stops[len(stops) - 1]
        self.stops = stops
        self.easings = easings
        self.coordinates = coordinates
        self.length = len(self.coordinates)
        self.channel_names = channel_names
        self.create = create
        self.progress = progress
        self.space = space
        self.out_space = out_space
        self.extrapolate = extrapolate
        self.current_easing = None  # type: Optional[Union[Callable[..., float], Mapping[str, Callable[..., float]]]]
        cs = self.create.CS_MAP[space]
        if isinstance(cs, Cylindrical):
            self.hue_index = cs.hue_index()
        else:
            self.hue_index = -1
        self.premultiplied = premultiplied

        # Ensure domain ascends.
        # If we have a domain of length 1, we will duplicate it.
        if domain is not None and domain:
            length = len(domain)

            # Ensure values are not descending
            d = [domain[0]]
            for index in range(length - 1):
                b = domain[index + 1]
                d.append(d[-1] if b <= d[-1] else b)

            # We need at least two values, so duplicate the first.
            if len(d) == 1:
                d.append(d[0])
            domain = d

        self.domain = [] if domain is None else domain  # type: List[float]

        self.setup()

    def setup(self) -> None:
        """Optional setup."""

    @abstractmethod
    def interpolate(
        self,
        point: float,
        index: int,
    ) -> Vector:
        """Interpolate."""

    def steps(
        self,
        steps: int = 2,
        max_steps: int = 1000,
        max_delta_e: float = 0,
        delta_e: Optional[str] = None
    ) -> List['Color']:
        """Steps."""

        actual_steps = steps

        # Allocate at least two steps if we are doing a maximum delta E,
        if max_delta_e != 0 and actual_steps < 2:
            actual_steps = 2

        # Make sure we don't start out allocating too many colors
        if max_steps is not None:
            actual_steps = min(actual_steps, max_steps)

        ret = []  # type: List[Tuple[float, Color]]
        if actual_steps == 1:
            ret = [(0.5, self(0.5))]
        elif actual_steps > 1:
            step = 1 / (actual_steps - 1)
            for i in range(actual_steps):
                p = i * step
                ret.append((p, self(p)))

        # Iterate over all the stops inserting stops in between all colors
        # if we have any two colors with a max delta greater than what was requested.
        # We inject between every stop to ensure the midpoint does not shift.
        if max_delta_e > 0:
            # Initial check to see if we need to insert more stops
            m_delta = 0.0
            for i in range(1, len(ret)):
                m_delta = max(
                    m_delta,
                    ret[i - 1][1].delta_e(
                        ret[i][1],
                        method=delta_e
                    )
                )

            # If we currently have delta over our limit inject more stops.
            # If inserting between every color would push us over the max_steps, halt.
            total = len(ret)
            while m_delta > max_delta_e and (total * 2 - 1 <= max_steps):
                # Inject stops while measuring again to see if it was sufficient
                m_delta = 0.0
                i = 1
                index = 1
                while index < total:
                    prev = ret[index - 1]
                    cur = ret[index]
                    p = (cur[0] + prev[0]) / 2
                    color = self(p)
                    m_delta = max(
                        m_delta,
                        color.delta_e(prev[1], method=delta_e),
                        color.delta_e(cur[1], method=delta_e)
                    )
                    ret.insert(index, (p, color))
                    total += 1
                    index += 2

        return [i[1] for i in ret]

    def premultiply(self, coords: Vector, alpha: Optional[float] = None) -> None:

        if alpha is not None:
            coords[-1] = alpha
        else:
            alpha = coords[-1]

        if alg.is_nan(alpha) or alpha == 1.0:
            return

        for i, value in enumerate(coords[:-1]):

            # Wrap the angle
            if i == self.hue_index:
                continue

            coords[i] = value * alpha

    def postdivide(self, coords: Vector) -> None:
        """Undo premultiplication of semi-transparent colors."""

        alpha = coords[-1]

        if alg.is_nan(alpha) or alpha in (0.0, 1.0):
            return

        for i, value in enumerate(coords[:-1]):

            # Wrap the angle
            if i == self.hue_index:
                continue

            coords[i] = value / alpha

    def begin(self, point: float, first: float, last: float, index: int) -> 'Color':
        """
        Begin interpolation.

        - Ensure point is relative to the stops.
        - Get the appropriate easing function.
        - Call interpolation.
        - Return a color
        """

        # Adjust stop to be relative to the given stops
        r = last - first
        if point < first:
            adjusted_time = point - first if self.extrapolate else 0
        elif point > last:
            adjusted_time = 1 + point - last if self.extrapolate else 1
        else:
            adjusted_time = (point - first) / r if r else 1

        # Do we have an easing function between these stops?
        self.current_easing = self.easings[index - 1]
        if self.current_easing is None:
            self.current_easing = self.progress

        # Interpolate color and return it
        coords = self.interpolate(adjusted_time, index)
        if self.premultiplied:
            self.postdivide(coords)

        # Create the color and ensure it is in the correct color space.
        color = self.create(self.space, coords[:-1], coords[-1])
        return color.convert(self.out_space, in_place=True)

    def ease(self, t: float, channel_index: int) -> float:
        """Provide a progression time and channel index."""

        progress = None
        if self.current_easing is not None:
            # Do we have an easing function, or mapping with a channel easing function?
            name = self.channel_names[channel_index]
            if isinstance(self.current_easing, Mapping):
                progress = self.current_easing.get(name)
                if progress is None:
                    progress = self.current_easing.get('all')
            else:
                progress = self.current_easing

        return progress(t) if progress is not None else t

    def scale(self, point: float) -> float:
        """
        Scale a point from a custom domain into a domain of 0 to 1.

        This allows a user to have a custom domain, but for us to adapt back to 0 and 1
        so that our logic can remain consistent.
        """

        if point < self.domain[0]:
            point = (point - self.domain[0]) / (self.domain[-1] - self.domain[0]) if self.extrapolate else 0.0
        elif point > self.domain[-1]:
            point = 1.0 + (point - self.domain[-1]) / (self.domain[-1] - self.domain[0]) if self.extrapolate else 1.0
        else:
            regions = len(self.domain) - 1
            size = (1 / regions)
            index = 0
            adjusted = 0.0
            for index in range(regions):
                a, b = self.domain[index:index + 2]
                if point >= a and point <= b:
                    l = b - a
                    adjusted = ((point - a) / l) if l else 0.0
                    break

            point = size * index + (adjusted * size)
        return point

    def __call__(self, point: float) -> 'Color':
        """Find which leg of the interpolation the request is between."""

        if self.domain:
            point = self.scale(point)

        # See if point extends past either the first or last stop
        if point < self.start:
            first, last = self.start, self.stops[1]
            return self.begin(point, first, last, 1)
        elif point > self.end:
            first, last = self.stops[self.length - 2], self.end
            return self.begin(point, first, last, self.length - 1)
        else:
            # Iterate stops to find where our point falls between
            first = self.start
            for i in range(1, self.length):
                last = self.stops[i]
                if point <= last:
                    return self.begin(point, first, last, i)
                first = last

        # We shouldn't ever hit this, but provided for typing.
        # If we do hit this, it would be a bug.
        raise RuntimeError('Iterpolation could not be found for {}'.format(point))  # pragma: no cover


class Interpolate(Plugin, metaclass=ABCMeta):
    """Interpolation plugin."""

    NAME = ""

    @abstractmethod
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
        """Get the interpolator object."""


def calc_stops(stops: Dict[int, float], count: int) -> Dict[int, float]:
    """Calculate stops."""

    # Ensure the first stop is set to zero if not explicitly set
    if 0 not in stops or stops[0] is None:
        stops[0] = 0

    last = stops[0] * 100
    highest = last
    empty = None
    final = {}

    # Build up normalized stops
    for i in range(count):
        value = stops.get(i)
        if value is not None:
            value *= 100

        # Found an empty hole, track the start
        if value is None and empty is None:
            empty = i - 1
            continue
        elif value is None:
            continue

        # We can't have a stop decrease in progression
        if value < last:
            value = last

        # Track the largest explicit value set
        if value > highest:
            highest = value

        # Fill in hole if one exists.
        # Holes will be evenly space between the
        # current and last stop.
        if empty is not None:
            r = i - empty
            increment = (value - last) / r
            for j in range(empty + 1, i):
                last += increment
                final[j] = last / 100
            empty = None

        # Set the stop and track it as the last
        last = value
        final[i] = last / 100

    # If there is a hole at the end, fill in the hole,
    # equally spacing the stops from the last to 100%.
    # If the last is greater than 100%, then all will
    # be equal to the last.
    if empty is not None:
        r = (count - 1) - empty
        if highest > 100:
            increment = 0
        else:
            increment = (100 - last) / r
        for j in range(empty + 1, count):
            last += increment
            final[j] = last / 100

    return final


def process_mapping(
    progress: Optional[Union[Mapping[str, Callable[..., float]], Callable[..., float]]],
    aliases: Mapping[str, str]
) -> Optional[Union[Callable[..., float], Mapping[str, Callable[..., float]]]]:
    """Process a mapping, such that it is not using aliases."""

    if not isinstance(progress, Mapping):
        return progress
    return {aliases.get(k, k): v for k, v in progress.items()}


def adjust_shorter(h1: float, h2: float, offset: float) -> Tuple[float, float]:
    """Adjust the given hues."""

    d = h2 - h1
    if d > 180:
        h2 -= 360.0
        offset -= 360.0
    elif d < -180:
        h2 += 360
        offset += 360.0
    return h2, offset


def adjust_longer(h1: float, h2: float, offset: float) -> Tuple[float, float]:
    """Adjust the given hues."""

    d = h2 - h1
    if 0 < d < 180:
        h2 -= 360.0
        offset -= 360.0
    elif -180 < d <= 0:
        h2 += 360
        offset += 360.0
    return h2, offset


def adjust_increase(h1: float, h2: float, offset: float) -> Tuple[float, float]:
    """Adjust the given hues."""

    if h2 < h1:
        h2 += 360.0
        offset += 360.0
    return h2, offset


def adjust_decrease(h1: float, h2: float, offset: float) -> Tuple[float, float]:
    """Adjust the given hues."""

    if h2 > h1:
        h2 -= 360.0
        offset -= 360.0
    return h2, offset


def normalize_hue(
    color1: Vector,
    color2: Optional[Vector],
    index: int,
    offset: float,
    hue: str,
    fallback: Optional[float]
) -> Tuple[Vector, float]:
    """Normalize hues according the hue specifier."""

    if hue == 'specified':
        return (color2 or color1), offset

    # Probably the first hue
    if color2 is None:
        color1[index] = util.constrain_hue(color1[index])
        return color1, offset

    if hue == 'shorter':
        adjuster = adjust_shorter
    elif hue == 'longer':
        adjuster = adjust_longer
    elif hue == 'increasing':
        adjuster = adjust_increase
    elif hue == 'decreasing':
        adjuster = adjust_decrease
    else:
        raise ValueError("Unknown hue adjuster '{}'".format(hue))

    c1 = color1[index] + offset
    c2 = util.constrain_hue(color2[index]) + offset

    # Adjust hue, handle gaps across `NaN`s
    if not alg.is_nan(c2):
        if not alg.is_nan(c1):
            c2, offset = adjuster(c1, c2, offset)
        elif fallback is not None:
            c2, offset = adjuster(fallback, c2, offset)

    color2[index] = c2
    return color2, offset


def carryforward_convert(color: 'Color', space: str) -> None:  # pragma: no cover
    """Carry forward undefined values during conversion."""

    cs1 = color._space
    cs2 = color.CS_MAP[space]
    channels = {'r': False, 'g': False, 'b': False, 'h': False, 'c': False, 'l': False, 'v': False}
    carry = []

    # Gather undefined channels
    if isinstance(cs1, RGBish):
        for i, name in zip(cs1.indexes(), ('r', 'g', 'b')):
            if alg.is_nan(color[i]):
                channels[name] = True
    elif isinstance(cs1, LChish):
        for i, name in zip(cs1.indexes(), ('l', 'c', 'h')):
            if alg.is_nan(color[i]):
                channels[name] = True
    elif isinstance(cs1, Labish):
        if alg.is_nan(color[cs1.indexes()[0]]):
            channels['l'] = True
    elif isinstance(cs1, HSLish):
        for i, name in zip(cs1.indexes(), ('h', 'c', 'l')):
            if alg.is_nan(color[i]):
                channels[name] = True
    elif isinstance(cs1, HSVish):
        for i, name in zip(cs1.indexes(), ('h', 'c', 'v')):
            if alg.is_nan(color[i]):
                channels[name] = True
    elif isinstance(cs1, Cylindrical):
        if alg.is_nan(color[cs1.hue_index()]):
            channels['h'] = True

    # Carry alpha forward if undefined
    if alg.is_nan(color[-1]):
        carry.append(-1)

    # Channels that need to be carried forward
    if isinstance(cs2, RGBish):
        indexes = cs2.indexes()
        for e, name in enumerate(('r', 'g', 'b')):
            if channels[name]:
                carry.append(indexes[e])
    elif isinstance(cs2, Labish):
        indexes = cs2.indexes()
        if channels['l']:
            carry.append(indexes[0])
    elif isinstance(cs2, LChish):
        indexes = cs2.indexes()
        for e, name in enumerate(('l', 'c', 'h')):
            if channels[name]:
                carry.append(indexes[e])
    elif isinstance(cs2, HSLish):
        indexes = cs2.indexes()
        for e, name in enumerate(('h', 'c', 'l')):
            if channels[name]:
                carry.append(indexes[e])
    elif isinstance(cs2, HSVish):
        indexes = cs2.indexes()
        for e, name in enumerate(('h', 'c', 'v')):
            if channels[name]:
                carry.append(indexes[e])
    elif isinstance(cs2, Cylindrical):
        if channels['h']:
            carry.append(cs2.hue_index())

    # Convert the color space
    color.convert(space, in_place=True)
    for i in carry:
        color[i] = alg.NaN


def interpolator(
    interpolator: str,
    create: Type['Color'],
    colors: Sequence[Union[ColorInput, stop, Callable[..., float]]],
    space: Optional[str],
    out_space: Optional[str],
    progress: Optional[Union[Mapping[str, Callable[..., float]], Callable[..., float]]],
    hue: str,
    premultiplied: bool,
    extrapolate: bool,
    domain: Optional[List[float]] = None,
    **kwargs: Any
) -> Interpolator:
    """Get desired blend mode."""

    plugin = create.INTERPOLATE_MAP.get(interpolator)
    if not plugin:
        raise ValueError("'{}' is not a recognized interpolator".format(interpolator))

    # Construct piecewise interpolation object
    stops = {}  # type: Any

    if space is None:
        space = create.INTERPOLATE

    if isinstance(colors[0], stop):
        current = create(colors[0].color)
        stops[0] = colors[0].stop
    elif not callable(colors[0]):
        current = create(colors[0])
        stops[0] = None
    else:
        raise ValueError('Cannot have an easing function as the first item in an interpolation list')

    if out_space is None:
        out_space = space

    # Adjust to space
    if space != current.space():
        if kwargs.get('_carryforward', False):  # pragma: no cover
            carryforward_convert(current, space)
        else:
            current.convert(space, in_place=True)

    offset = 0.0
    hue_index = current._space.hue_index() if isinstance(current._space, Cylindrical) else -1

    # Normalize hue
    norm_coords = current[:]
    fallback = None
    if hue_index >= 0:
        h = norm_coords[hue_index]
        norm_coords, offset = normalize_hue(norm_coords, None, hue_index, offset, hue, fallback)
        if not alg.is_nan(h):
            fallback = h

    easing = None  # type: Any
    easings = []  # type: Any
    coords = [norm_coords]

    i = 0
    for x in colors[1:]:

        # Normalize all colors as Piecewise objects
        if isinstance(x, stop):
            i += 1
            stops[i] = x.stop
            color = current.new(x.color)
        elif callable(x):
            easing = x
            continue
        else:
            i += 1
            color = current.new(x)
            stops[i] = None

        # Adjust color to space
        if space != color.space():
            if kwargs.get('_carryforward', False):  # pragma: no cover
                carryforward_convert(color, space)
            else:
                color.convert(space, in_place=True)

        # Normalize the hue
        norm_coords = color[:]
        if hue_index >= 0:
            h = norm_coords[hue_index]
            norm_coords, offset = normalize_hue(current[:], norm_coords, hue_index, offset, hue, fallback)
            if not alg.is_nan(h):
                fallback = h

        # Create an entry interpolating the current color and the next color
        coords.append(norm_coords)
        easings.append(easing if easing is not None else progress)

        # The "next" color is now the "current" color
        easing = None
        current = color

    i += 1
    if i < 2:
        raise ValueError('Need at least two colors to interpolate')

    # Calculate stops
    stops = calc_stops(stops, i)

    # Send the interpolation list along with the stop map to the Piecewise interpolator
    return plugin.interpolator(
        coords,
        current._space.channels,
        create,
        easings,
        stops,
        space,
        out_space,
        process_mapping(progress, current._space.CHANNEL_ALIASES),
        premultiplied,
        extrapolate,
        domain,
        **kwargs
    )
