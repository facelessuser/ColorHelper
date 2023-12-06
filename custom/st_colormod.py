"""Color-mod."""
import re
from ..lib.coloraide import ColorMatch
from ..lib.coloraide.css import parse, serialize
from ..lib.coloraide import util
from ..lib.coloraide import algebra as alg
from ..lib.coloraide.spaces.hwb.css import HWB as HWBORIG
from collections.abc import Mapping
from itertools import zip_longest as zipl
import functools
import math
from ColorHelper.ch_util import get_base_color, COLOR_PARTS

RE_CHAN_VALUE = re.compile(r'(?i)(?:[+\-]?(?:[0-9]*\.)?[0-9]+(?:e[-+]?[0-9]+)?(?:%|deg|rad|turn|grad)?|none)')

BASE = get_base_color()

WHITE = [1.0] * 3
BLACK = [0.0] * 3

TOKENS = {
    "units": re.compile(
        r"""(?xi)
        # Some number of units separated by valid separators
        (?:
            {float} |
            {angle} |
            {percent} |
            \#(?:{hex}{{6}}(?:{hex}{{2}})?|{hex}{{3}}(?:{hex})?) |
            [\w][\w\d]*
        )
        """.format(**COLOR_PARTS)
    ),
    "functions": re.compile(r'(?i)[\w][\w\d]*\('),
    "separators": re.compile(r'(?:{comma}|{space}|{slash})'.format(**COLOR_PARTS))
}

RE_ADJUSTERS = {
    "alpha": re.compile(
        r"""
        (?xi)
        \s+a(?:lpha)?\(\s*
        (?:(\+\s+|\-\s+)?({strict_percent}|{strict_float})|(\*)?\s*({strict_percent}|{strict_float}))
        \s*\)
        """.format(
            **COLOR_PARTS
        )
    ),
    "saturation": re.compile(
        r'(?i)\s+s(?:aturation)?\((\+\s|\-\s|\*)?\s*({strict_percent})\s*\)'.format(**COLOR_PARTS)
    ),
    "lightness": re.compile(
        r'(?i)\s+l(?:ightness)?\((\+\s|\-\s|\*)?\s*({strict_percent})\s*\)'.format(**COLOR_PARTS)
    ),
    "min-contrast_start": re.compile(r'(?i)\s+min-contrast\(\s*'),
    "blend_start": re.compile(r'(?i)\s+blenda?\(\s*'),
    "end": re.compile(r'(?i)\s*\)')
}

RE_HUE = re.compile(r'(?i){angle}'.format(**COLOR_PARTS))
RE_COLOR_START = re.compile(r'(?i)color\(\s*')
RE_BLEND_END = re.compile(r'(?i)\s+({strict_percent})(?:\s+(rgb|hsl|hwb))?\s*\)'.format(**COLOR_PARTS))
RE_BRACKETS = re.compile(r'(?:(\()|(\))|[^()]+)')
RE_MIN_CONTRAST_END = re.compile(r'(?i)\s+({strict_float})\s*\)'.format(**COLOR_PARTS))
RE_VARS = re.compile(r'(?i)(?:(?<=^)|(?<=[\s\t\(,/]))(var\(\s*([-\w][-\w\d]*)\s*\))(?!\()(?=[\s\t\),/]|$)')

HWB_MATCH = re.compile(
    r"""(?xi)
    \b(hwb)\(\s*
    (?:
        # Space separated format
        {angle}{loose_space}{percent}{loose_space}{percent}(?:{slash}(?:{percent}|{float}))? |
        # comma separated format
        {angle}{comma}{percent}{comma}{percent}(?:{comma}(?:{percent}|{float}))?
    )
    \s*\)
    """.format(**COLOR_PARTS)
)


def bracket_match(match, string, start, fullmatch):
    """
    Make sure we can acquire a complete `func()` before we replace variables.

    We mainly do this so we can judge the real size before we alter the string with variables.
    """

    end = None
    if match.match(string, start):
        brackets = 1
        for m in RE_BRACKETS.finditer(string, start + 6):
            if m.group(2):
                brackets -= 1
            elif m.group(1):
                brackets += 1

            if brackets == 0:
                end = m.end(2)
                break
    return end if (not fullmatch or end == len(string)) else None


def validate_vars(var, good_vars):
    """
    Validate variables.

    We will blindly replace values, but if we are fairly confident they follow
    the pattern of a valid, complete unit, if you replace them in a bad place,
    it will break the color (as it should) and if not, it is likely to parse fine,
    unless it breaks the syntax of the color being evaluated.
    """

    for k, v in var.items():
        v = v.strip()
        start = 0
        need_sep = False
        length = len(v)
        while True:
            if start == length:
                good_vars[k] = v
                break
            try:
                # Each item should be separated by some valid separator
                if need_sep:
                    m = TOKENS["separators"].match(v, start)
                    if m:
                        start = m.end(0)
                        need_sep = False
                        continue
                    else:
                        break

                # Validate things like `rgb()`, `contrast()` etc.
                m = TOKENS["functions"].match(v, start)
                if m:
                    end = None
                    brackets = 1
                    for m in RE_BRACKETS.finditer(v, start + 6):
                        if m.group(2):
                            brackets -= 1
                        elif m.group(1):
                            brackets += 1

                        if brackets == 0:
                            end = m.end(0)
                            break
                    if end is None:
                        break
                    start = end
                    need_sep = True
                    continue

                # Validate that units such as percents, floats, hex colors, etc.
                m = TOKENS["units"].match(v, start)
                if m:
                    start = m.end(0)
                    need_sep = True
                    continue
                break
            except Exception:
                break


def _var_replace(m, var=None, parents=None):
    """Replace variables but try to prevent infinite recursion."""

    name = m.group(2)
    replacement = var.get(m.group(2))
    string = replacement if replacement and name not in parents is not None else ""
    parents.add(name)
    return RE_VARS.sub(functools.partial(_var_replace, var=var, parents=parents), string)


def handle_vars(string, variables, parents=None):
    """Handle CSS variables."""

    temp_vars = {}
    validate_vars(variables, temp_vars)
    parent_vars = set() if parents is None else parents

    return RE_VARS.sub(functools.partial(_var_replace, var=temp_vars, parents=parent_vars), string)


class HWB(HWBORIG):
    """HWB class that allows commas."""

    def match(self, string, start=0, fullmatch=True):
        """Match a CSS color string."""

        m = HWB_MATCH.match(string, start)
        if m is not None and (not fullmatch or m.end(0) == len(string)):
            return parse.parse_channels(
                list(RE_CHAN_VALUE.findall(string[m.end(1) + 1:m.end(0) - 1])),
                self.CHANNELS, scaled=True
            ), m.end(0)
        return None

    def to_string(
        cls,
        parent,
        *,
        alpha=None,
        precision=None,
        percent=None,
        fit=True,
        none=False,
        color: bool = False,
        comma: bool = False,
        **kwargs
    ) -> str:
        """Convert to CSS."""

        if percent is None:
            percent = False if color else True

        return serialize.serialize_css(
            parent,
            func='hwb',
            alpha=alpha,
            precision=precision,
            fit=fit,
            none=none,
            color=kwargs.get('color', False),
            percent=True if comma else percent,
            scale=100,
            legacy=comma
        )


class ColorMod:
    """Color utilities."""

    def __init__(self, fullmatch=True):
        """Associate with parent."""

        self.OP_MAP = {
            "": self._op_null,
            "*": self._op_mult,
            "+": self._op_add,
            "-": self._op_sub
        }

        self.adjusting = False
        self._color = None
        self.fullmatch = fullmatch

    @staticmethod
    def _op_mult(a, b):
        """Multiply."""

        return a * b

    @staticmethod
    def _op_add(a, b):
        """Multiply."""

        return a + b

    @staticmethod
    def _op_sub(a, b):
        """Multiply."""

        return a - b

    @staticmethod
    def _op_null(a, b):
        """Multiply."""

        return b

    def _adjust(self, string, start=0):
        """Adjust."""

        nested = self.adjusting
        self.adjusting = True

        color = None
        done = False
        old_parent = self._color
        hue = None

        try:
            m = RE_COLOR_START.match(string, start)
            if m:
                start = m.end(0)
                m = RE_HUE.match(string, start)
                if m:
                    hue = parse.norm_angle(m.group(0))
                    color = Color("hsl", [hue, 1, 0.5]).convert("srgb")
                    start = m.end(0)
                if color is None:
                    m = RE_COLOR_START.match(string, start)
                    if m:
                        color2, start = self._adjust(string, start=start)
                        if color2 is None:
                            raise ValueError("Found unterminated or invalid 'color('")
                        color = color2.convert("srgb")
                        if not color.is_nan("hsl.hue"):
                            hue = color.get("hsl.hue")
                if color is None:
                    obj = Color.match(string, start=start, fullmatch=False)
                    if obj is not None:
                        color = obj.color
                        if color.space != "srgb":
                            color = color.convert("srgb")
                        if not color.is_nan("hsl.hue"):
                            hue = color.get("hsl.hue")
                        start = obj.end

            if color is not None:
                self._color = color
                self._color.clone().clip()

                while not done:
                    m = None
                    name = None
                    for key, pattern in RE_ADJUSTERS.items():
                        name = key
                        m = pattern.match(string, start)
                        if m:
                            start = m.end(0)
                            break
                    if m is None:
                        break

                    if name == "alpha":
                        start, hue = self.process_alpha(m, hue)
                    elif name in ("saturation", "lightness"):
                        start, hue = self.process_hwb_hsl_channels(name, m, hue)
                    elif name == "min-contrast_start":
                        start, hue = self.process_min_contrast(m, string, hue)
                    elif name == "blend_start":
                        start, hue = self.process_blend(m, string, hue)
                    elif name == "end":
                        done = True
                        start = m.end(0)
                    else:
                        break

                    self._color.clone().clip()
            else:
                raise ValueError('Could not calculate base color')
        except Exception:
            pass

        if not done or (self.fullmatch and start != len(string)):
            result = None
        else:
            result = self._color

        self._color = old_parent

        if not nested:
            self.adjusting = False

        return result, start

    def adjust_base(self, base, string):
        """Adjust base."""

        self._color = base
        pattern = "color({} {})".format(self._color.clone().clip().to_string(precision=-1), string)
        color, _ = self._adjust(pattern)
        if color is not None:
            self._color.update(color)
        else:
            raise ValueError(
                "'{}' doesn't appear to be a valid and/or supported CSS color or color-mod instruction".format(string)
            )

    def adjust(self, string, start=0):
        """Adjust."""

        color, end = self._adjust(string, start=start)
        return color, end

    def process_alpha(self, m, hue):
        """Process alpha."""

        if m.group(2):
            value = m.group(2)
        else:
            value = m.group(4)
        if value.endswith('%'):
            value = float(value.strip('%')) * parse.SCALE_PERCENT
        else:
            value = float(value)
        op = ""
        if m.group(1):
            op = m.group(1).strip()
        elif m.group(3):
            op = m.group(3).strip()
        self.alpha(value, op=op)
        return m.end(0), hue

    def process_hwb_hsl_channels(self, name, m, hue):
        """Process HWB and HSL channels (except hue)."""

        value = m.group(2)
        value = float(value.strip('%')) * parse.SCALE_PERCENT
        op = m.group(1).strip() if m.group(1) else ""
        getattr(self, name)(value, op=op, hue=hue)
        if not self._color.is_nan("hsl.hue"):
            hue = self._color.get("hsl.hue")
        return m.end(0), hue

    def process_blend(self, m, string, hue):
        """Process blend."""

        start = m.end(0)
        alpha = m.group(0).strip().startswith('blenda')
        m = RE_COLOR_START.match(string, start)
        if m:
            color2, start = self._adjust(string, start=start)
            if color2 is None:
                raise ValueError("Found unterminated or invalid 'color('")
        else:
            color2 = None
            obj = Color.match(string, start=start, fullmatch=False)
            if obj is not None:
                color2 = obj.color
                start = obj.end
            if color2 is None:
                raise ValueError("Could not find a valid color for 'blend'")
        m = RE_BLEND_END.match(string, start)
        if m:
            value = float(m.group(1).strip('%')) * parse.SCALE_PERCENT
            space = "srgb"
            if m.group(2):
                space = m.group(2).lower()
                if space == "rgb":
                    space = "srgb"
            start = m.end(0)
        else:
            raise ValueError("Found unterminated or invalid 'blend('")

        value = alg.clamp(value, 0.0, 1.0)
        self.blend(color2, 1.0 - value, alpha, space=space)
        if not self._color.is_nan("hsl.hue"):
            hue = self._color.get("hsl.hue")
        return start, hue

    def process_min_contrast(self, m, string, hue):
        """Process blend."""

        # Gather the min-contrast parameters
        start = m.end(0)
        m = RE_COLOR_START.match(string, start)
        if m:
            color2, start = self._adjust(string, start=start)
            if color2 is None:
                raise ValueError("Found unterminated or invalid 'color('")
        else:
            color2 = None
            obj = Color.match(string, start=start, fullmatch=False)
            if obj is not None:
                color2 = obj.color
                start = obj.end
        m = RE_MIN_CONTRAST_END.match(string, start)
        if m:
            value = float(m.group(1))
            start = m.end(0)
        else:
            raise ValueError("Found unterminated or invalid 'min-contrast('")

        this = self._color.convert("srgb")
        color2 = color2.convert("srgb")
        color2[-1] = 1.0

        self.min_contrast(this, color2, value)
        self._color.update(this)
        if not self._color.is_nan("hsl.hue"):
            hue = self._color.get("hsl.hue")
        return start, hue

    def min_contrast(self, color1, color2, target):
        """
        Get the color with the best contrast.

        This mimics Sublime Text's custom `min-contrast` for `color-mod` (now defunct - the CSS version).
        It ensure the color has at least the specified contrast ratio.

        While there seems to be slight differences with ours and Sublime, maybe due to some rounding,
        this essentially fulfills the intention of their min-contrast.
        """

        ratio = color1.contrast(color2)

        # Already meet the minimum contrast or the request is impossible
        if ratio > target or target < 1:
            return

        lum2 = color2.luminance()

        is_dark = lum2 < 0.5
        orig = color1.convert("hwb")
        if is_dark:
            primary = "whiteness"
            secondary = "blackness"
            min_mix = orig[primary] * 100
            max_mix = 100
        else:
            primary = "blackness"
            secondary = "whiteness"
            min_mix = orig[primary] * 100
            max_mix = 100
        orig_ratio = ratio
        last_ratio = 0
        last_mix = 0
        last_other = 0

        temp = orig.clone()
        while abs(min_mix - max_mix) > 0.2:
            mid_mix = round((max_mix + min_mix) / 2, 1)
            mid_other = (
                orig.get(secondary) -
                ((mid_mix - orig.get(primary) * 100) / (1 - orig.get(primary) * 100)) * orig.get(secondary) * 100
            )
            temp.set(primary, mid_mix / 100)
            temp.set(secondary, mid_other / 100)
            ratio = temp.contrast(color2)

            if ratio < target:
                min_mix = mid_mix
            else:
                max_mix = mid_mix

            if (
                (last_ratio < target and ratio > last_ratio) or
                (ratio > target and ratio < last_ratio)
            ):
                last_ratio = ratio
                last_mix = mid_mix
                last_other = mid_other

        # Can't find a better color
        if last_ratio < ratio and orig_ratio > last_ratio:
            return

        # Use the best, last values
        coords = [
            orig['hue'],
            last_mix / 100,
            last_other / 100
        ] if is_dark else [
            orig['hue'],
            last_other / 100,
            last_mix / 100
        ]
        final = orig.new("hwb", coords)
        final = final.convert('srgb')
        # If we are lightening the color, then we'd like to round up to ensure we are over the luminance threshold
        # as sRGB will clip off decimals. If we are darkening, then we want to just floor the values as the algorithm
        # leans more to the light side.
        rnd = alg.round_half_up if is_dark else math.floor
        final = Color("srgb", [rnd(c * 255.0) / 255.0 for c in final[:-1]], final[-1])
        color1.update(final)

    def blend(self, color, percent, alpha=False, space="srgb"):
        """Blend color."""

        space = space.lower()
        if space not in ("srgb", "hsl", "hwb"):
            raise ValueError(
                "ColorMod's does not support the '{}' colorspace, only 'srgb', 'hsl', and 'hwb' are supported"
            ).format(space)
        this = self._color.convert(space) if self._color.space() != space else self._color

        if color.space() != space:
            color.convert(space, in_place=True)

        new_color = this.mix(color, percent, space=space, premultiplied=False)
        if not alpha:
            new_color[-1] = color[-1]
        self._color.update(new_color)

    def alpha(self, value, op=""):
        """Alpha."""

        this = self._color
        op = self.OP_MAP.get(op, self._op_null)
        this[-1] = op(this[-1], value)
        self._color.update(this)

    def lightness(self, value, op="", hue=None):
        """Lightness."""

        this = self._color.convert("hsl") if self._color.space() != "hsl" else self._color
        if this.is_nan('hue') and hue is not None:
            this['hue'] = hue
        op = self.OP_MAP.get(op, self._op_null)
        this['lightness'] = op(this['lightness'], value)
        self._color.update(this)

    def saturation(self, value, op="", hue=None):
        """Saturation."""

        this = self._color.convert("hsl") if self._color.space() != "hsl" else self._color
        if this.is_nan("hue") and hue is not None:
            this['hue'] = hue
        op = self.OP_MAP.get(op, self._op_null)
        this['saturation'] = op(this['saturation'], value)
        self._color.update(this)


class Color(BASE):
    """Color modify class."""

    def __init__(self, color, data=None, alpha=util.DEF_ALPHA, *, variables=None, **kwargs):
        """Initialize."""

        super().__init__(color, data, alpha, variables=variables, **kwargs)

    @classmethod
    def _parse(
        cls,
        color,
        data=None,
        alpha=util.DEF_ALPHA,
        *,
        variables=None,
        **kwargs
    ):
        """Parse the color."""

        obj = None
        if isinstance(color, str):

            # Parse a color space name and coordinates
            if data is not None:
                s = color
                space_class = cls.CS_MAP.get(s)
                if not space_class:
                    raise ValueError("'{}' is not a registered color space".format(s))
                num_channels = len(space_class.CHANNELS)
                num_data = len(data)
                if num_data < num_channels:
                    data = list(data) + [alg.NaN] * (num_channels - num_data)
                coords = [alg.clamp(float(v), *c.limit) for c, v in zipl(space_class.CHANNELS, data)]
                coords.append(alg.clamp(float(alpha), *space_class.channels[-1].limit))
                obj = space_class, coords

            # Parse a CSS string
            else:
                m = cls._match(color, fullmatch=True, variables=variables)
                if m is None:
                    raise ValueError("'{}' is not a valid color".format(color))
                coords = [alg.clamp(float(v), *c.limit) for c, v in zipl(m[0].CHANNELS, m[1])]
                coords.append(alg.clamp(float(m[2]), *m[0].channels[-1].limit))
                obj = m[0], coords

        # Handle a color instance
        elif isinstance(color, BASE):
            space_class = cls.CS_MAP.get(color.space())
            if not space_class:
                raise ValueError("'{}' is not a registered color space".format(color.space()))
            obj = space_class, color[:]

        # Handle a color dictionary
        elif isinstance(color, Mapping):
            obj = cls._parse(color['space'], color['coords'], color.get('alpha', 1.0))

        else:
            raise TypeError("'{}' is an unrecognized type".format(type(color)))

        if obj is None:
            raise ValueError("Could not process the provided color")
        return obj

    @classmethod
    def _match(cls, string, start=0, fullmatch=False, variables=None):
        """
        Match a color in a buffer and return a color object.

        This must return the color space, not the Color object.
        """

        # Handle variable
        end = None
        is_mod = False
        if variables:
            m = RE_VARS.match(string, start)
            if m and (not fullmatch or len(string) == m.end(0)):
                end = m.end(0)
                start = 0
                string = string[start:end]
                string = handle_vars(string, variables)
                variables = None

        temp = bracket_match(RE_COLOR_START, string, start, fullmatch)
        if end is None and temp:
            end = temp
            is_mod = True
        elif end is not None and temp is not None:
            is_mod = True

        if is_mod:
            if variables:
                string = handle_vars(string, variables)
            obj, match_end = ColorMod(fullmatch).adjust(string, start)
            if obj is not None:
                return obj._space, obj[:-1], obj[-1], start, (end if end is not None else match_end)
        else:
            return super()._match(string, start, fullmatch)
        return None

    @classmethod
    def match(
        cls,
        string: str,
        start: int = 0,
        fullmatch: bool = False
    ):
        """Match color."""

        m = cls._match(string, start, fullmatch, variables=None)
        if m is not None:
            return ColorMatch(cls(m[0].NAME, m[1], m[2]), m[3], m[4])
        return None

    def new(self, color, data=None, alpha=util.DEF_ALPHA, *, variables=None, **kwargs):
        """Create new color object."""

        return type(self)(color, data, alpha, variables=variables, **kwargs)

    def update(self, color, data=None, alpha=util.DEF_ALPHA, *, norm=True, variables=None, **kwargs):
        """Update the existing color space with the provided color."""

        space = self.space()
        self._space, self._coords = self._parse(
            color, data=data, alpha=alpha, variables=variables, **kwargs
        )
        if self._space.NAME != space:
            self.convert(space, in_place=True, norm=norm)
        return self

    def mutate(self, color, data=None, alpha=util.DEF_ALPHA, *, variables=None, **kwargs):
        """Mutate the current color to a new color."""

        self._space, self._coords = self._parse(
            color, data=data, alpha=alpha, variables=variables, **kwargs
        )
        return self


Color.register(HWB(), overwrite=True)
