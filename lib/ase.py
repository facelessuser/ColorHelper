# -*- coding: utf-8 -*-
"""
ASE.

Copyright (c) 2015 - 2016 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
from __future__ import unicode_literals
import struct
import re
import sys
from io import BytesIO

PY3 = sys.version_info >= (3, 0)

if PY3:
    uchr = chr
    ustr = str
else:
    uchr = unichr  # noqa
    ustr = unicode  # noqa

# Blocks
GROUP_START = 0xC001
GROUP_END = 0xC002
COLOR_ENTRY = 0x0001

# Default color type
COLOR_TYPE = 0x0000

# 1 * unsigned short string size
DB_STRING_SIZE_SZ = 2

# 4 char color type
# 3 * float rgb channel
# 1 * unsigned short
RGB_SIZE = 18

# ASE version
ASE_VERSION = 1

# For calculating size of bytes from struct format string
UNIT_SIZE = {
    'c': 1,
    'b': 1,
    'B': 1,
    '?': 1,
    'h': 2,
    'H': 2,
    'i': 4,
    'I': 4,
    'l': 4,
    'L': 4,
    'q': 8,
    'Q': 8,
    'f': 4,
    'd': 8
}

RE_UNIT = re.compile(r'\s*(\d*)([cbB?hHiIlLqQfd])\s*')


def split_channels(rgb):
    """
    Split an RGB color into channels.

    Take a color of the format #RRGGBBAA (alpha optional and will be stripped)
    and convert to a tuple with format (r, g, b).
    """

    return (
        float(int(rgb[1:3], 16)) / 255.0,
        float(int(rgb[3:5], 16)) / 255.0,
        float(int(rgb[5:7], 16)) / 255.0
    )


def format_byte_size(fmt):
    """Determine the number of bytes form the fmt string."""

    b = 0
    for m in RE_UNIT.finditer(fmt):
        count = int(m.group(1)) if m.group(1) else 1
        b += count * UNIT_SIZE[m.group(2)]
    return b


class _Writer(object):
    """ASE writer."""

    def __init__(self, ase):
        """Open an ASE file for writing."""

        if ase is None:
            self.bin = BytesIO()
        else:
            self.bin = open(ase, 'wb')

    def write_header(self, total_blocks):
        """Write the ASE file header."""

        self.write_string('ASEF')
        self.write('2H', (1, 0))
        self.write('i', total_blocks)

    def write_group_start(self, title):
        """Write group starting block."""

        self.write('H', GROUP_START)
        self.write('i', ((len(title) + 1) * 2) + DB_STRING_SIZE_SZ)
        self.write('H', len(title) + 1)
        self.write_string(title, double_byte=True)

    def write_group_end(self):
        """Write group closing block."""

        self.write('H', GROUP_END)
        self.write('i', 0)

    def write_color(self, color, name=None):
        """Write the RGB color entry."""

        self.write('H', COLOR_ENTRY)
        if name is None:
            name = ''
        self.write('i', ((len(name) + 1) * 2) + DB_STRING_SIZE_SZ + RGB_SIZE)
        self.write('H', len(name) + 1)
        self.write_string(name, double_byte=True)

        r, g, b = split_channels(color)
        self.write_string('RGB ')
        self.write('f', r)
        self.write('f', g)
        self.write('f', b)
        self.write('H', COLOR_TYPE)

    def write(self, fmt, data):
        """
        Write data.

        If single point of data is given, convert it to a tuple.
        """

        if not isinstance(data, (tuple, list, bytes, ustr)):
            data = (data,)

        fmt = '>' + fmt
        if not PY3:
            fmt = fmt.encode('utf-8')
        if isinstance(data, ustr):
            data = [ord(c) for c in data]

        self.bin.write(struct.pack(fmt, *data))

    def write_string(self, string, double_byte=False):
        """Write either a normal string or double byte string."""

        string
        fmt = ('%dB' if not double_byte else '%dH') % len(string)
        self.write(fmt, string)
        if double_byte:
            self.write('H', 0)

    def close(self):
        """Close binary file."""

        self.bin.close()


class _Reader(object):
    """ASE reader."""

    def __init__(self, ase, byte_string=False):
        """Open file for reading."""

        self._string = byte_string
        if byte_string:
            self.bin = BytesIO(ase)
        else:
            self.bin = open(ase, 'rb')

    def read_header(self):
        """"Parse the header."""

        self.signature = self.read_string(4)
        self.version = self.read('2H')
        self.total_blocks = int(self.read('i')[0])

    def read(self, fmt):
        """Read the and unpack binary data."""

        fmt = '>' + fmt
        if not PY3:
            fmt = fmt.encode('utf-8')
        return struct.unpack(fmt, self.bin.read(format_byte_size(fmt)))

    def read_string(self, block_size, double_byte=False):
        """Retrieve either a normal string or double byte string."""

        fmt = ('B' if not double_byte else 'H') * block_size
        string = ''
        if double_byte:
            db_string = self.read(fmt)
            for c in db_string[:-1]:
                string += uchr(c)
        else:
            b_string = self.read(fmt)
            for c in b_string:
                string += uchr(c)
        return string

    def get_block(self):
        """Get block id."""

        return int(self.read('H')[0])

    def get_block_length(self):
        """Get block length."""

        return int(self.read('i')[0])

    def get_string_length(self):
        """Get length of double byte string."""

        return int(self.read('H')[0])

    def get_color(self):
        """Get RGB color."""

        color_type = self.read_string(4)
        if 'RGB ' != color_type:
            raise Exception('Only RGB is supported at this time, not %s!' % color_type)
        r = int(float(self.read('f')[0]) * 255.0)
        g = int(float(self.read('f')[0]) * 255.0)
        b = int(float(self.read('f')[0]) * 255.0)
        self.read('H')
        return "#%02x%02x%02x" % (r, g, b)

    def close(self):
        """Close the binary."""

        self.bin.close()

    def read_palettes(self):
        """Parse therough the ASE file returning palettes."""

        palette = {}
        while self.total_blocks > 0:
            block = self.get_block()
            if block == GROUP_START:
                palette = {}
                self.get_block_length()
                title_length = self.get_string_length()
                palette['title'] = self.read_string(title_length, double_byte=True)
                palette['colors'] = []
                self.total_blocks -= 1
                while block != GROUP_END:
                    block = self.get_block()
                    if block == COLOR_ENTRY:
                        self.get_block_length()
                        self.total_blocks -= 1
                        color_entry = {}
                        name_length = self.get_string_length()
                        color_entry['name'] = self.read_string(name_length, double_byte=True)
                        color_entry['color'] = self.get_color()
                        palette['colors'].append(color_entry)
                    elif block == GROUP_END:
                        self.total_blocks -= 1
                        self.get_block_length()
                        yield palette
                    else:
                        raise Exception('Expected group end or color entry block!')
            else:
                raise Exception('Expected group start block!')


def loads(ase):
    """Read the ASE file from a byte string and return the palettes."""

    binary = _Reader(ase, byte_string=True)
    try:
        binary.read_header()
        palattes = []

        for palette in binary.read_palettes():
            palattes.append(palette)
    except:
        binary.close()
        raise
    binary.close()
    return palattes


def dumps(ase, palettes):
    """Write an ASE file to a byte string with the given palettes."""

    text = b''
    total_blocks = len(palettes) * 2
    for p in palettes:
        total_blocks += len(p.get("colors", []))

    binary = _Writer(None)
    try:
        binary.write_header(total_blocks)

        for p in palettes:
            binary.write_group_start(p["title"])
            for c in p['colors']:
                binary.write_color(c['color'], c.get('name'))
            binary.write_group_end()
        binary.bin.seek(0)
        text = binary.bin.read()
    except:
        binary.close()
        raise
    binary.close()
    return text


def dump(ase, palettes):
    """Write an ASE file with the given palettes."""

    total_blocks = len(palettes) * 2
    for p in palettes:
        total_blocks += len(p.get("colors", []))

    binary = _Writer(ase)
    try:
        binary.write_header(total_blocks)

        for p in palettes:
            binary.write_group_start(p["title"])
            for c in p['colors']:
                binary.write_color(c['color'], c.get('name'))
            binary.write_group_end()
    except:
        binary.close()
        raise
    binary.close()


def load(ase):
    """Read the ASE file and return the palettes."""

    binary = _Reader(ase)
    try:
        binary.read_header()
        palattes = []

        for palette in binary.read_palettes():
            palattes.append(palette)
    except:
        binary.close()
        raise
    binary.close()
    return palattes


if __name__ == "__main__":
    import unittest

    palettes = [
        {
            # Testing unicode
            # http://www.colourlovers.com/palette/629637/(%E2%97%95%E3%80%9D%E2%97%95)
            'title': '(Ã¢â€”â€¢Ã£â‚¬ÂÃ¢â€”â€¢)',
            'colors': [
                {'color': '#fe4365', 'name': 'Sugar Hearts You'},
                {'color': '#fc9d9a', 'name': 'Party Confetti'},
                {'color': '#f9cdad', 'name': 'Sugar Champagne'},
                {'color': '#c8c8a9', 'name': 'Bursts Of Euphoria'},
                {'color': '#83af9b', 'name': 'Happy Balloons'}
            ]
        },
        {
            # Testing more than one palette in a file
            # http://www.colourlovers.com/palette/1930/cheer_up_emo_kid
            'title': 'cheer up emo kid',
            'colors': [
                {'color': '#556270', 'name': 'Mighty Slate'},
                {'color': '#4ecdc4', 'name': 'Pacifica'},
                {'color': '#c7f464', 'name': 'apple chic'},
                {'color': '#ff6b6b', 'name': 'Cheery Pink'},
                {'color': '#c44d58', 'name': "grandma's pillow"}
            ],
        }
    ]

    dump('test1.ase', palettes)
    palettes2 = load('test1.ase')

    test = unittest.TestCase()
    test.assertEqual(palettes, palettes2)
