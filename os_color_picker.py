"""OS specific color pickers."""
import sublime
import subprocess
from coloraide import Color

MAC_CHOOSE_COLOR = '''\
tell current application to choose color default color {{{}, {}, {}}}
'''

UINT = 65535

if sublime.platform() == "windows":
    import ctypes

    class CHOOSECOLOR(ctypes.Structure):
        """Structure for `CHOOSECOLOR`."""

        _fields_ = [('lStructSize', ctypes.c_uint32),
                    ('hwndOwner', ctypes.c_void_p),
                    ('hInstance', ctypes.c_void_p),
                    ('rgbResult', ctypes.c_uint32),
                    ('lpCustColors', ctypes.POINTER(ctypes.c_uint32)),
                    ('Flags', ctypes.c_uint32),
                    ('lCustData', ctypes.c_void_p),
                    ('lpfnHook', ctypes.c_void_p),
                    ('lpTemplateName', ctypes.c_wchar_p)]

    CC_SOLIDCOLOR = 0x80
    CC_RGBINIT = 0x01
    CC_FULLOPEN = 0x02
    ChooseColorW = ctypes.windll.Comdlg32.ChooseColorW
    ChooseColorW.argtypes = [ctypes.POINTER(CHOOSECOLOR)]
    ChooseColorW.restype = ctypes.c_int32


class _ColorPicker:
    """Generic color picker class."""

    def __init__(self, color):
        """Initialize the color."""

        self.color = color

    def pick(self):
        """Pick the color."""

        return self.color


class MacPick(_ColorPicker):
    """MacOS color picker."""

    def pick(self):
        """Pick the color."""

        color = self.color.convert('srgb')
        coords = [x * UINT for x in color.fit(in_place=True).coords()]
        try:
            p = subprocess.Popen(
                ['osascript', '-e', MAC_CHOOSE_COLOR.format(*coords)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE
            )
            out = p.communicate()
            returncode = p.returncode
            if returncode:
                color = self.color
            else:
                color = Color("srgb", [int(x) / UINT for x in out[0].split(b', ')])
                self.color = color
        except Exception:
            color = self.color

        return color


class WinPick(_ColorPicker):
    """
    Windows color picker.

    https://docs.microsoft.com/en-us/windows/win32/api/commdlg/ns-commdlg-choosecolorw-r1
    """

    def pick(self):
        """Pick the color."""

        color = self.color.convert('srgb')
        hx = color.to_string(hex=True, alpha=False)[1:]
        bgr = int(hx[4:6] + hx[2:4] + hx[0:2], 16)

        picker = CHOOSECOLOR()
        picker.lStructSize = ctypes.sizeof(picker)
        CustomColors = ctypes.c_uint32 * 16  # noqa: N806
        picker.lpCustColors = CustomColors()
        picker.Flags = CC_SOLIDCOLOR | CC_FULLOPEN | CC_RGBINIT
        picker.rgbResult = ctypes.c_uint32(bgr)

        if ChooseColorW(ctypes.byref(picker)):
            hx = '{:06x}'.format(picker.rgbResult)
            color = Color('srgb', [int(hx[4:6], 16), int(hx[2:4], 16), int(hx[0:2], 16)])
            self.color = color
        else:
            color = self.color
        return color


class LinuxPick(_ColorPicker):
    """
    Linux color picker.

    https://apps.kde.org/en/kcolorchooser
    """

    def pick(self):
        """Pick the color."""

        color = self.color.convert('srgb')
        hx = color.to_string(hex=True, alpha=False)
        try:
            p = subprocess.Popen(
                ['kcolorchooser', '--print', '--color', hx],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE
            )
            out = p.communicate()
            returncode = p.returncode
            if returncode:
                color = self.color
            else:
                color = Color(out[0].decode('utf-8').strip())
                self.color = color
        except Exception:
            color = self.color

        return color


def pick(color):
    """Get the color picker for the OS."""

    platform = sublime.platform()
    if platform == "windows":
        picker = WinPick(color)
    elif platform == "osx":
        picker = MacPick(color)
    else:
        picker = LinuxPick(color)
    return picker.pick()
