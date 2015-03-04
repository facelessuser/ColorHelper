'''
RGBA
Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
'''

import re
from colorsys import rgb_to_hls, hls_to_rgb, rgb_to_hsv, hsv_to_rgb

RGB_CHANNEL_SCALE = 1.0 / 255.0
HUE_SCALE = 1.0 / 360.0


def clamp(value, mn, mx):
    return max(min(value, mx), mn)


class RGBA(object):
    r = None
    g = None
    b = None
    a = None
    color_pattern = re.compile(r"^#(?:([A-Fa-f\d]{6})([A-Fa-f\d]{2})?|([A-Fa-f\d]{3}))")

    def __init__(self, s=None):
        if s is None:
            s = "#000000FF"
        self.r, self.g, self.b, self.a = self._split_channels(s)

    def _split_channels(self, s):
        def alpha_channel(alpha):
            return int(alpha, 16) if alpha else 0xFF

        m = self.color_pattern.match(s)
        assert(m is not None)
        if m.group(1):
            return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16), alpha_channel(m.group(2))
        else:
            return int(s[1] * 2, 16), int(s[2] * 2, 16), int(s[3] * 2, 16), 0xFF

    def get_rgba(self):
        return "#%02X%02X%02X%02X" % (self.r, self.g, self.b, self.a)

    def get_rgb(self):
        return "#%02X%02X%02X" % (self.r, self.g, self.b)

    def apply_alpha(self, background="#000000FF"):
        def tx_alpha(cf, af, cb, ab):
            return int(abs(cf * (af / 255.0) + cb * (ab / 255.0) * (1 - (af / 255.0)))) & 0xFF

        if self.a < 0xFF:
            r, g, b, a = self._split_channels(background)

            self.r, self.g, self.b = (tx_alpha(self.r, self.a, r, a), tx_alpha(self.g, self.a, g, a), tx_alpha(self.b, self.a, b, a))

        return self.get_rgb()

    def luminance(self):
        return clamp(int(round(0.299 * self.r + 0.587 * self.g + 0.114 * self.b)), 0, 255)

    def tohsv(self):
        return rgb_to_hsv(self.r * RGB_CHANNEL_SCALE, self.g * RGB_CHANNEL_SCALE, self.b * RGB_CHANNEL_SCALE)

    def fromhsv(self, h, s, v):
        r, g, b = hsv_to_rgb(h, s, v)
        self.r = int(round(r * 255)) & 0xFF
        self.g = int(round(g * 255)) & 0xFF
        self.b = int(round(b * 255)) & 0xFF

    def tohls(self):
        return rgb_to_hls(self.r * RGB_CHANNEL_SCALE, self.g * RGB_CHANNEL_SCALE, self.b * RGB_CHANNEL_SCALE)

    def fromhls(self, h, l, s):
        r, g, b = hls_to_rgb(h, l, s)
        self.r = int(round(r * 255)) & 0xFF
        self.g = int(round(g * 255)) & 0xFF
        self.b = int(round(b * 255)) & 0xFF

    def colorize(self, deg):
        h, l, s = self.tohls()
        h = clamp(deg * HUE_SCALE, 0.0, 1.0)
        self.fromhls(h, l, s)

    def hue(self, deg):
        d = deg * HUE_SCALE
        h, l, s = self.tohls()
        h = h + d
        while h > 1.0:
            h -= 1.0
        while h < 0.0:
            h += 1.0
        self.fromhls(h, l, s)

    def invert(self):
        self.r ^= 0xFF
        self.g ^= 0xFF
        self.b ^= 0xFF

    def saturation(self, factor):
        h, l, s = self.tohls()
        s = clamp(s * factor, 0.0, 1.0)
        self.fromhls(h, l, s)

    def grayscale(self):
        luminance = self.luminance() & 0xFF
        self.r = luminance
        self.g = luminance
        self.b = luminance

    def sepia(self):
        r = clamp(int((self.r * .393) + (self.g * .769) + (self.b * .189)), 0, 255) & 0xFF
        g = clamp(int((self.r * .349) + (self.g * .686) + (self.b * .168)), 0, 255) & 0xFF
        b = clamp(int((self.r * .272) + (self.g * .534) + (self.b * .131)), 0, 255) & 0xFF
        self.r, self.g, self.b = r, g, b

    def brightness(self, factor):
        # Caculate brightness based on RGB luminance.
        # Maybe HLS or HSV brightness adjustment is better?
        def get_overage(c):
            if c < 0.0:
                o = 0.0 + c
                c = 0.0
            elif c > 255.0:
                o = c - 255.0
                c = 255.0
            else:
                o = 0.0
            return o, c

        def distribute_overage(c, o, s):
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

        channels = ["r", "g", "b"]
        total_lumes = clamp(self.luminance() + (255.0 * factor) - 255.0, 0.0, 255.0)

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
                overage, components[count] = get_overage(components[count])
                if overage:
                    slots.remove(c)
                    components = list(distribute_overage(components, overage, slots))
                count += 1

            self.r = clamp(int(round(components[0])), 0, 255) & 0xFF
            self.g = clamp(int(round(components[1])), 0, 255) & 0xFF
            self.b = clamp(int(round(components[2])), 0, 255) & 0xFF
