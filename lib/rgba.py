"""
RGBA.

Licensed under MIT
Copyright (c) 2012 - 2016 Isaac Muse <isaacmuse@gmail.com>
"""
import re
from colorsys import rgb_to_hls, hls_to_rgb, rgb_to_hsv, hsv_to_rgb
import decimal

RGB_CHANNEL_SCALE = 1.0 / 255.0
HUE_SCALE = 1.0 / 360.0
PERCENT_TO_CHANNEL = 255.0 / 100.0
CHANNEL_TO_PERCENT = 100.0 / 255.0
SCALE_PERCENT = 1 / 100.0
SCALE_HALF_PERCENT = 1 / 50.0

CS_RGB = 0
CS_HSL = 1
CS_HWB = 2

OP_NULL = 0
OP_SCALE = 1
OP_ADD = 2
OP_SUB = 3


def rgb_blend_channel(c1, c2, f):
    """Blend the red, green, blue style channel."""

    return clamp(
        round_int(abs(c1 * f + c2 * (1 - f))),
        0, 255
    )


def percent_blend_channel(c1, c2, f):
    """Blend the percent style channel."""

    return clamp(
        abs(c1 * f + c2 * (1 - f)),
        0.0, 1.0
    )


def hue_blend_channel(c1, c2, f):
    """Blend the hue style channel."""

    c1 *= 360.0
    c2 *= 360.0

    if abs(c1 - c2) > 180.0:
        if c1 < c2:
            c1 += 360.0
        else:
            c2 += 360.0

    value = abs(c1 * f + c2 * (1 - f))
    while value > 360.0:
        value -= 360.0

    return value * HUE_SCALE


def mix_channel(cf, af, cb, ab):
    """
    Mix the color channel.

    `cf`: Channel foreground
    `af`: Alpha foreground
    `cb`: Channel background
    `ab`: Alpha background

    The foreground is overlayed on the secondary color it is to be mixed with.
    The alpha channels are applied and the colors mix.
    """

    return clamp(
        round_int(
            abs(
                cf * (af * RGB_CHANNEL_SCALE) + cb * (ab * RGB_CHANNEL_SCALE) * (1 - (af * RGB_CHANNEL_SCALE))
            )
        ),
        0, 255
    )


def clamp(value, mn, mx):
    """Clamp the value to the the given minimum and maximum."""

    return max(min(value, mx), mn)


def round_int(dec):
    """Round float to nearest int using expected rounding."""

    return int(decimal.Decimal(dec).quantize(decimal.Decimal('0'), decimal.ROUND_HALF_DOWN))


class RGBA(object):
    """RGBA object for converting between color formats or applying filters to the color."""

    r = None
    g = None
    b = None
    a = None
    color_pattern = re.compile(r"^#(?:([A-Fa-f\d]{6})([A-Fa-f\d]{2})?|([A-Fa-f\d]{3}))")

    def __init__(self, s=None):
        """Initialize."""

        if s is None:
            s = "#000000FF"
        self.r, self.g, self.b, self.a = self._split_channels(s)

    def _split_channels(self, s):
        """Split the color into color channels: red, green, blue, alpha."""

        def alpha_channel(alpha):
            """Get alpha channel."""
            return int(alpha, 16) if alpha else 0xFF

        m = self.color_pattern.match(s)
        assert(m is not None)
        if m.group(1):
            return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16), alpha_channel(m.group(2))
        else:
            return int(s[1] * 2, 16), int(s[2] * 2, 16), int(s[3] * 2, 16), 0xFF

    def get_rgba(self):
        """Get the RGB color with the alpha channel."""

        return "#%02X%02X%02X%02X" % (self.r, self.g, self.b, self.a)

    def get_rgb(self):
        """Get the `RGB` value."""

        return "#%02X%02X%02X" % (self.r, self.g, self.b)

    def apply_alpha(self, background="#000000FF"):
        """
        Apply the given transparency with the given background.

        This gives a color that represents what the eye sees with
        the transparent color against the given background.
        """

        if self.a < 0xFF:
            r, g, b, a = self._split_channels(background)

            self.r = mix_channel(self.r, self.a, r, a)
            self.g = mix_channel(self.g, self.a, g, a)
            self.b = mix_channel(self.b, self.a, b, a)

        return self.get_rgb()

    def get_luminance(self):
        """Get perceived luminance."""

        return clamp(round_int(0.299 * self.r + 0.587 * self.g + 0.114 * self.b), 0, 255)

    def get_true_luminance(self):
        """Get true luminance."""

        l = self.tohls()[1]
        return clamp(round_int(l * 255.0), 0, 255)

    def alpha(self, factor, op=OP_SCALE):
        """Adjust alpha."""

        if op == OP_SCALE:
            self.a = round_int(clamp(self.a + (255.0 * factor) - 255.0, 0.0, 255.0))
        elif op == OP_ADD:
            self.a = round_int(clamp(self.a + (self.a * factor), 0.0, 255.0))
        elif op == OP_SUB:
            self.a = round_int(clamp(self.a - (self.a * factor), 0.0, 255.0))
        else:
            self.a = 255.0 * factor

    def red(self, factor, op=OP_SCALE):
        """Adjust red."""

        if op == OP_SCALE:
            self.r = round_int(clamp(self.r + (255.0 * factor) - 255.0, 0.0, 255.0))
        elif op == OP_ADD:
            self.r = round_int(clamp(self.r + (self.r * factor), 0.0, 255.0))
        elif op == OP_SUB:
            self.r = round_int(clamp(self.r - (self.r * factor), 0.0, 255.0))
        else:
            self.a = 255.0 * factor

    def green(self, factor, op=OP_SCALE):
        """Adjust green."""

        if op == OP_SCALE:
            self.g = round_int(clamp(self.g + (255.0 * factor) - 255.0, 0.0, 255.0))
        elif op == OP_ADD:
            self.g = round_int(clamp(self.g + (self.g * factor), 0.0, 255.0))
        elif op == OP_SUB:
            self.g = round_int(clamp(self.g - (self.g * factor), 0.0, 255.0))
        else:
            self.a = 255.0 * factor

    def blue(self, factor, op=OP_SCALE):
        """Adjust blue."""

        if op == OP_SCALE:
            self.b = round_int(clamp(self.b + (255.0 * factor) - 255.0, 0.0, 255.0))
        elif op == OP_ADD:
            self.b = round_int(clamp(self.b + (self.b * factor), 0.0, 255.0))
        elif op == OP_SUB:
            self.b = round_int(clamp(self.b - (self.b * factor), 0.0, 255.0))
        else:
            self.a = 255.0 * factor

    def blend(self, color, percent, alpha=False, color_space=CS_RGB):
        """Blend color."""

        r, g, b, a = self._split_channels(color)
        factor = clamp(clamp(float(percent), 0.0, 100.0) * SCALE_PERCENT, 0.0, 1.0)

        if color_space == CS_RGB:
            self.r = rgb_blend_channel(self.r, r, factor)
            self.g = rgb_blend_channel(self.g, g, factor)
            self.b = rgb_blend_channel(self.b, b, factor)
        elif color_space == CS_HSL:
            orig_h, orig_l, orig_s = self.tohls()
            blend_h, blend_l, blend_s = rgb_to_hls(r * RGB_CHANNEL_SCALE, g * RGB_CHANNEL_SCALE, b * RGB_CHANNEL_SCALE)
            h = hue_blend_channel(orig_h, blend_h, factor)
            l = percent_blend_channel(orig_l, blend_l, factor)
            s = percent_blend_channel(orig_s, blend_s, factor)
            self.fromhls(h, l, s)
        elif color_space == CS_HWB:
            orig_h, orig_w, orig_b = self.tohwb()
            blend_h, s, v = rgb_to_hsv(r * RGB_CHANNEL_SCALE, g * RGB_CHANNEL_SCALE, b * RGB_CHANNEL_SCALE)
            blend_w = (1.0 - s) * v
            blend_b = 1.0 - v
            h = hue_blend_channel(orig_h, blend_h, factor)
            w = percent_blend_channel(orig_w, blend_w, factor)
            b = percent_blend_channel(orig_b, blend_b, factor)
            self.fromhwb(h, w, b)
        else:
            raise ValueError('Invalid color space value: {}'.format(str(color_space)))

        if alpha:
            self.a = rgb_blend_channel(self.a, a, factor)

    def luminance(self, factor, op=OP_SCALE):
        """Get true luminance."""

        h, l, s = self.tohls()
        if op == OP_SCALE:
            l = clamp(l + factor - 1.0, 0.0, 1.0)
        elif op == OP_ADD:
            l = clamp(l + (l * factor), 0.0, 1.0)
        elif op == OP_SUB:
            l = clamp(l - (l * factor), 0.0, 1.0)
        else:
            l = clamp(factor, 0.0, 1.0)
        self.fromhls(h, l, s)

    def tohsv(self):
        """Convert to `HSV` color format."""

        return rgb_to_hsv(self.r * RGB_CHANNEL_SCALE, self.g * RGB_CHANNEL_SCALE, self.b * RGB_CHANNEL_SCALE)

    def fromhsv(self, h, s, v):
        """Convert to `RGB` from `HSV`."""

        r, g, b = hsv_to_rgb(h, s, v)
        self.r = clamp(round_int(r * 255.0), 0, 255)
        self.g = clamp(round_int(g * 255.0), 0, 255)
        self.b = clamp(round_int(b * 255.0), 0, 255)

    def tohls(self):
        """Convert to `HLS` color format."""

        return rgb_to_hls(self.r * RGB_CHANNEL_SCALE, self.g * RGB_CHANNEL_SCALE, self.b * RGB_CHANNEL_SCALE)

    def fromhls(self, h, l, s):
        """Convert to `RGB` from `HSL`."""

        r, g, b = hls_to_rgb(h, l, s)
        self.r = clamp(round_int(r * 255.0), 0, 255)
        self.g = clamp(round_int(g * 255.0), 0, 255)
        self.b = clamp(round_int(b * 255.0), 0, 255)

    def tohwb(self):
        """Convert to `HWB` from `RGB`."""

        h, s, v = self.tohsv()
        w = (1.0 - s) * v
        b = 1.0 - v
        return h, w, b

    def fromhwb(self, h, w, b):
        """Convert to `RGB` from `HWB`."""

        # Normalize white and black
        # w + b <= 1.0
        if w + b > 1.0:
            norm_factor = 1.0 / (w + b)
            w *= norm_factor
            b *= norm_factor

        # Convert to `HSV` and then to `RGB`
        s = 1.0 - (w / (1.0 - b))
        v = 1.0 - b
        r, g, b = hsv_to_rgb(h, s, v)
        self.r = clamp(round_int(r * 255.0), 0, 255)
        self.g = clamp(round_int(g * 255.0), 0, 255)
        self.b = clamp(round_int(b * 255.0), 0, 255)

    def colorize(self, deg):
        """Colorize the color with the given hue."""

        h, l, s = self.tohls()
        h = clamp(deg * HUE_SCALE, 0.0, 1.0)
        self.fromhls(h, l, s)

    def hue(self, deg):
        """Shift the hue."""

        d = deg * HUE_SCALE
        h, l, s = self.tohls()
        h = h + d
        while h > 1.0:
            h -= 1.0
        while h < 0.0:
            h += 1.0
        self.fromhls(h, l, s)

    def contrast(self, factor):
        """Adjust contrast."""

        # Algorithm can't handle any thing beyond +/-255 (or a factor from 0 - 2)
        # Convert factor between (-255, 255)
        f = (clamp(factor, 0.0, 2.0) - 1.0) * 255.0
        f = (259 * (f + 255)) / (255 * (259 - f))

        # Increase/decrease contrast accordingly.
        self.r = clamp(round_int((f * (self.r - 128)) + 128), 0, 255)
        self.g = clamp(round_int((f * (self.g - 128)) + 128), 0, 255)
        self.b = clamp(round_int((f * (self.b - 128)) + 128), 0, 255)

    def invert(self):
        """Invert the color."""

        self.r ^= 0xFF
        self.g ^= 0xFF
        self.b ^= 0xFF

    def saturation(self, factor, op=OP_SCALE):
        """Saturate or unsaturate the color by the given factor."""

        h, l, s = self.tohls()
        if op == OP_SCALE:
            s = clamp(s + factor - 1.0, 0.0, 1.0)
        elif op == OP_ADD:
            s = clamp(s + (s * factor), 0.0, 1.0)
        elif op == OP_SUB:
            s = clamp(s - (s * factor), 0.0, 1.0)
        else:
            s = clamp(factor, 0.0, 1.0)
        self.fromhls(h, l, s)

    def grayscale(self):
        """Convert the color with a grayscale filter."""

        luminance = self.get_luminance()
        self.r = luminance
        self.g = luminance
        self.b = luminance

    def sepia(self):
        """Apply a sepia filter to the color."""

        r = clamp(round_int((self.r * .393) + (self.g * .769) + (self.b * .189)), 0, 255)
        g = clamp(round_int((self.r * .349) + (self.g * .686) + (self.b * .168)), 0, 255)
        b = clamp(round_int((self.r * .272) + (self.g * .534) + (self.b * .131)), 0, 255)
        self.r, self.g, self.b = r, g, b

    def _get_overage(self, c):
        """Get overage."""

        if c < 0.0:
            o = 0.0 + c
            c = 0.0
        elif c > 255.0:
            o = c - 255.0
            c = 255.0
        else:
            o = 0.0
        return o, c

    def _distribute_overage(self, c, o, s):
        """Distribute overage."""

        channels = len(s)
        if channels == 0:
            return c
        parts = o / len(s)
        if "r" in s and "g" in s:
            c = c[0] + parts, c[1] + parts, c[2]
        elif "r" in s and "b" in s:
            c = c[0] + parts, c[1], c[2] + parts
        elif "g" in s and "b" in s:
            c = c[0], c[1] + parts, c[2] + parts
        elif "r" in s:
            c = c[0] + parts, c[1], c[2]
        elif "g" in s:
            c = c[0], c[1] + parts, c[2]
        else:  # "b" in s:
            c = c[0], c[1], c[2] + parts
        return c

    def brightness(self, factor):
        """
        Adjust the brightness by the given factor.

        Brightness is determined by perceived luminance.
        """

        channels = ["r", "g", "b"]
        total_lumes = clamp(self.get_luminance() + (255.0 * factor) - 255.0, 0.0, 255.0)

        if total_lumes == 255.0:
            # white
            self.r, self.g, self.b = 0xFF, 0xFF, 0xFF
        elif total_lumes == 0.0:
            # black
            self.r, self.g, self.b = 0x00, 0x00, 0x00
        else:
            # Adjust Brightness
            pts = (total_lumes - 0.299 * self.r - 0.587 * self.g - 0.114 * self.b)
            slots = set(channels)
            components = [float(self.r) + pts, float(self.g) + pts, float(self.b) + pts]
            count = 0
            for c in channels:
                overage, components[count] = self._get_overage(components[count])
                if overage:
                    slots.remove(c)
                    components = list(self._distribute_overage(components, overage, slots))
                count += 1

            self.r = clamp(round_int(components[0]), 0, 255)
            self.g = clamp(round_int(components[1]), 0, 255)
            self.b = clamp(round_int(components[2]), 0, 255)
