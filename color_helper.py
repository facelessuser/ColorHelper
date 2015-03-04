"""
ColorHelper

Copyright (c) 2015 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
from ColorHelper.lib.color_box import color_box, palette_preview
from ColorHelper.lib.scheme_lum import scheme_lums
from ColorHelper.lib.rgba import RGBA
import ColorHelper.lib.webcolors as webcolors
import threading
from time import time, sleep
import re

css = None
pref_settings = None
ch_settings = None
border_color = '#333333'
back_arrow = None
cross = None

COLOR_RE = re.compile(
    r'''(?x)
    (?P<hex>\#(?P<hex_content>(?:[\dA-Fa-f]{3}){1,2})) |
    (?P<rgb>rgb\(\s*(?P<rgb_content>(?:\d+\s*,\s*){2}\d+)\s*\)) |
    (?P<rgba>rgba\(\s*(?P<rgba_content>(?:\d+\s*,\s*){3}(?:(?:\d*\.\d+)|\d))\s*\)) |
    (?P<hsl>hsl\(\s*(?P<hsl_content>\d+\s*,\s*\d+%\s*,\s*\d+%)\s*\)) |
    (?P<hsla>hsla\(\s*(?P<hsla_content>\d+\s*,\s*(?:\d+%\s*,\s*){2}(?:(?:\d*\.\d+)|\d))\s*\)) |
    (?P<hash>\#) |
    (?P<rgb_open>rgb\() |
    (?P<rgba_open>rgba\() |
    (?P<hsl_open>hsl\() |
    (?P<hsla_open>hsla\()
    '''
)

if 'ch_thread' not in globals():
    ch_thread = None


###########################
# Main Code
###########################
class ColorHelperCommand(sublime_plugin.TextCommand):
    def on_navigate(self, href):
        """ Handle link clicks """
        if href.startswith('#'):
            self.insert_color(href)
        elif not href.startswith('__'):
            self.show_colors(href, update=True)
        elif href == '__close__':
            self.view.hide_popup()
        elif href == '__palettes__':
            self.show_palettes(update=True)
        elif href == '__info__':
            self.show_color_info(update=True)

    def insert_color(self, target_color):
        sels = self.view.sel()
        if (len(sels) == 1 and sels[0].size() == 0):
            try:
                web_color = webcolors.hex_to_name(target_color)
            except:
                web_color = None
            point = sels[0].begin()
            visible = self.view.visible_region()
            start = point - 50
            end = point + 50
            convert_rgb = False
            convert_hsl = False
            alpha = None
            region = sublime.Region(point)
            if start < visible.begin():
                start = visible.begin()
            if end > visible.end():
                end = visible.end()
            bfr = self.view.substr(sublime.Region(start, end))
            ref = point - start
            found = False
            for m in COLOR_RE.finditer(bfr):
                if ref >= m.start(0) and ref < m.end(0):
                    found = True
                    if m.group('hex'):
                        region = sublime.Region(m.start('hex') + start, m.end('hex') + start)
                        break
                    elif m.group('rgb'):
                        if web_color:
                            region = sublime.Region(m.start('rgb') + start, m.end('rgb') + start)
                        else:
                            region = sublime.Region(m.start('rgb_content') + start, m.end('rgb_content') + start)
                            convert_rgb = True
                        break
                    elif m.group('rgba'):
                        web_color = None
                        region = sublime.Region(m.start('rgba_content') + start, m.end('rgba_content') + start)
                        convert_rgb = True
                        content = [x.strip() for x in m.group('rgba_content').split(',')]
                        alpha = content[3]
                        break
                    elif m.group('hsl'):
                        if web_color:
                            region = sublime.Region(m.start('hsl') + start, m.end('hsl') + start)
                        else:
                            region = sublime.Region(m.start('hsl_content') + start, m.end('hsl_content') + start)
                            convert_hsl = True
                        break
                    elif m.group('hsla'):
                        web_color = None
                        region = sublime.Region(m.start('hsla_content') + start, m.end('hsla_content') + start)
                        convert_hsl = True
                        content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
                        alpha = content[3]
                        break
                    elif m.group('hash'):
                        region = sublime.Region(m.start('hash') + start, m.end('hash') + start)
                        break
                    elif m.group('rgb'):
                        if not web_color:
                            convert_rgb = True
                        break
                    elif m.group('rgba'):
                        convert_rgb = True
                        alpha = '1'
                        break
                    elif m.group('hsl'):
                        if not web_color:
                            convert_hsl = True
                        break
                    elif m.group('rgb'):
                        convert_hsl = True
                        alpha = '1'
                        break
                    else:
                        found = False
            if not found:
                word_region = self.view.word(sels[0])
                word = self.view.substr(word_region)
                try:
                    webcolors.name_to_hex(word).lower()
                    region = word_region
                except:
                    pass
            if web_color:
                value = web_color
            elif convert_rgb:
                value = "%d, %d, %d" % (
                    int(target_color[1:3], 16),
                    int(target_color[3:5], 16),
                    int(target_color[5:7], 16)
                )
                if alpha:
                    value += ', %s' % alpha
            elif convert_hsl:
                hsl = RGBA(target_color)
                h, l, s = hsl.tohls()
                value = "%d, %d%%, %d%%" % (
                    int('%.0f' % (h * 360.0)),
                    int('%.0f' % (s * 100.0)),
                    int('%.0f' % (l * 100.0))
                )
                if alpha:
                    value += ', %s' % alpha
            else:
                value = target_color
            self.view.sel().subtract(sels[0])
            self.view.sel().add(region)
            self.view.run_command("insert", {"characters": value})
        self.view.hide_popup()

    def format_palettes(self, color_list, label, caption=None):
        """ Format color palette previews """
        colors = ['<h1 class="header">%s</h1>' % label]
        if caption:
            colors.append('<span class="caption">%s</span><br>' % caption)
        colors.append(
            '<a href="%s">%s</a>' % (
                label,
                palette_preview(color_list, border_color)
            )
        )
        return ''.join(colors)

    def format_colors(self, color_list, label):
        """ Format colors under palette """
        colors = ['<h1 class="header">%s</h1>' % label]
        count = 0
        for f in color_list:
            if count != 0 and (count % 8 == 0):
                colors.append('<br><br>')
            elif count != 0:
                if sublime.platform() == 'windows':
                    colors.append('&nbsp; ')
                else:
                    colors.append('&nbsp;')
            colors.append('<a href="%s">%s</a>' % (f, color_box(f, border_color, size=32)))
            count += 1
        return ''.join(colors)

    def format_info(self, color):
        """ Format the selected color info """
        rgba = RGBA(color)

        try:
            web_color = webcolors.hex_to_name(color)
        except:
            web_color = None

        info = ['<h1 class="header">%s</h1>' % color]
        if web_color is not None:
            info.append('<strong>%s</strong><br><br>' % web_color)
        info.append('<a href="__palettes__">%s</a><br><br>' % color_box(color, border_color, size=64))
        info.append(
            '<span class="key">r:</span> %d ' % rgba.r +
            '<span class="key">g:</span> %d ' % rgba.g +
            '<span class="key">b:</span> %d<br>' % rgba.b
        )
        h, s, v = rgba.tohsv()
        info.append(
            '<span class="key">h:</span> %.0f ' % (h * 360.0) +
            '<span class="key">s:</span> %.0f ' % (s * 100.0) +
            '<span class="key">v:</span> %.0f<br>' % (v * 100.0)
        )
        h, l, s = rgba.tohls()
        info.append(
            '<span class="key">h:</span> %.0f ' % (h * 360.0) +
            '<span class="key">s:</span> %.0f ' % (s * 100.0) +
            '<span class="key">l:</span> %.0f<br>' % (l * 100.0)
        )
        return ''.join(info)

    def show_palettes(self, update=False):
        """ Show preview of all palettes """
        html = [
            '<style>%s</style>' % (css if css is not None else '') +
            '<div class="content">'
            # '<a href="__close__"><img style="width: 16px; height: 16px;" src="%s"></a>' % cross
        ]
        if not self.no_info:
            html.append('<a href="__info__"><img style="width: 16px; height: 16px;" src="%s"></a>' % back_arrow)
        for palette in ch_settings.get("palettes", []):
            html.append(self.format_palettes(palette['colors'], palette['name'], palette.get('caption')))
        html.append('</div>')

        if update:
            self.view.update_popup(''.join(html))
        else:
            self.view.show_popup(
                ''.join(html), location=-1, max_width=600,
                on_navigate=self.on_navigate
            )

    def show_colors(self, palette_name, update=False):
        """ Show colors under the given palette """
        target = None
        for palette in ch_settings.get("palettes", []):
            if palette_name == palette['name']:
                target = palette

        if target is not None:
            html = [
                '<style>%s</style>' % (css if css is not None else '') +
                '<div class="content">' +
                # '<a href="__close__"><img style="width: 16px; height: 16px;" src="%s"></a>' % cross +
                '<a href="__palettes__"><img style="width: 16px; height: 16px;" src="%s"></a>' % back_arrow +
                self.format_colors(target['colors'], target['name']) +
                '</div>'
            ]

            if update:
                self.view.update_popup(''.join(html))
            else:
                self.view.show_popup(
                    ''.join(html), location=-1, max_width=600,
                    on_navigate=self.on_navigate
                )

    def show_color_info(self, update=False):
        """ Show the color under the cursor """

        color = None
        sels = self.view.sel()
        if (len(sels) == 1 and sels[0].size() == 0):
            point = sels[0].begin()
            visible = self.view.visible_region()
            start = point - 50
            end = point + 50
            if start < visible.begin():
                start = visible.begin()
            if end > visible.end():
                end = visible.end()
            bfr = self.view.substr(sublime.Region(start, end))
            ref = point - start
            for m in COLOR_RE.finditer(bfr):
                if ref >= m.start(0) and ref < m.end(0):
                    if m.group('hex'):
                        content = m.group('hex_content')
                        if len(content) == 6:
                            color = "%02x%02x%02x" % (
                                int(content[0:2], 16), int(content[2:4], 16), int(content[4:6], 16)
                            )
                        else:
                            color = "%02x%02x%02x" % (
                                int(content[0:1] * 2, 16), int(content[1:2] * 2, 16), int(content[2:3] * 2, 16)
                            )
                        break
                    elif m.group('rgb'):
                        content = [x.strip() for x in m.group('rgb_content').split(',')]
                        color = "%02x%02x%02x" % (
                            int(content[0]), int(content[1]), int(content[2])
                        )
                        break
                    elif m.group('rgba'):
                        content = [x.strip() for x in m.group('rgba_content').split(',')]
                        color = "%02x%02x%02x%02x" % (
                            int(content[0]), int(content[1]), int(content[2]),
                            int('%.0f' % (float(content[3]) * 255.0))
                        )
                        break
                    elif m.group('hsl'):
                        content = [x.strip().rstrip('%') for x in m.group('hsl_content').split(',')]
                        rgba = RGBA()
                        h = float(content[0]) / 360.0
                        s = float(content[1]) / 100.0
                        l = float(content[2]) / 100.0
                        rgba.fromhls(h, l, s)
                        color = rgba.get_rgb()[1:]
                        break
                    elif m.group('hsla'):
                        content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
                        rgba = RGBA()
                        h = float(content[0]) / 360.0
                        s = float(content[1]) / 100.0
                        l = float(content[2]) / 100.0
                        rgba.fromhls(h, l, s)
                        color = rgba.get_rgb()[1:]
                        color += "%02X" % int('%.0f' % (float(content[3]) * 255.0))
                        break
            if color is None:
                word = self.view.substr(self.view.word(sels[0]))
                try:
                    color = webcolors.name_to_hex(word).lower()[1:]
                except:
                    pass
        if color is not None:
            html = [
                '<style>%s</style>' % (css if css is not None else '') +
                '<div class="content">' +
                # '<a href="__close__"><img style="width: 16px; height: 16px;" src="%s"></a>' % cross +
                self.format_info('#' + color.lower()) +
                '</div>'
            ]
            if update:
                self.view.update_popup(''.join(html))
            else:
                self.view.show_popup(
                    ''.join(html), location=-1, max_width=600,
                    on_navigate=self.on_navigate
                )
        elif update:
            self.view.hide_popup()

    def run(self, edit, palette_picker=False, palette_name=None):
        """ Run the specified tooltip """
        self.no_info = True
        if palette_name:
            self.show_colors(palette_name)
        elif palette_picker:
            self.show_palettes()
        else:
            self.no_info = False
            self.show_color_info()


###########################
# Threading
###########################
class ColorHelperListener(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        """ Flag that we need to show a tooltip """
        if ch_thread.ignore_all:
            return
        now = time()
        ch_thread.modified = True
        ch_thread.time = now

    def on_modified(self, view):
        """ Flag that we need to show a tooltip """
        if ch_thread.ignore_all:
            return
        now = time()
        ch_thread.modified = True
        ch_thread.time = now


class ChThread(threading.Thread):
    """ Load up defaults """

    def __init__(self):
        """ Setup the thread """
        self.reset()
        threading.Thread.__init__(self)

    def reset(self):
        """ Reset the thread variables """
        self.wait_time = 0.12
        self.time = time()
        self.modified = False
        self.ignore_all = False
        self.abort = False

    def payload(self):
        """ Code to run """
        self.modified = False
        self.ignore_all = True
        window = sublime.active_window()
        view = window.active_view()
        if view is not None:
            info = False
            execute = False
            sels = view.sel()
            if (
                len(sels) == 1 and sels[0].size() == 0
                and view.score_selector(sels[0].begin(), 'meta.property-value.css')
            ):
                point = sels[0].begin()
                visible = view.visible_region()
                start = point - 50
                end = point + 50
                if start < visible.begin():
                    start = visible.begin()
                if end > visible.end():
                    end = visible.end()
                bfr = view.substr(sublime.Region(start, end))
                ref = point - start
                for m in COLOR_RE.finditer(bfr):
                    if ref >= m.start(0) and ref < m.end(0):
                        if (
                            m.group('hex') or m.group('rgb') or m.group('rgba') or
                            m.group('hsl') or m.group('hsla')
                        ):
                            info = True
                            execute = True
                        break
                    elif ref == m.end(0):
                        if (
                            m.group('hash') or m.group('rgb_open') or m.group('rgba_open') or
                            m.group('hsl_open') or m.group('hsla_open')
                        ):
                            execute = True
                        break
                if not execute:
                    word = view.substr(view.word(sels[0]))
                    try:
                        webcolors.name_to_hex(word)
                        execute = True
                        info = True
                    except:
                        pass
                if execute:
                    view.run_command('color_helper', {"palette_picker": not info})
        self.ignore_all = False
        self.time = time()

    def kill(self):
        """ Kill thread """
        self.abort = True
        while self.is_alive():
            pass
        self.reset()

    def run(self):
        """ Thread loop """
        while not self.abort:
            if self.modified is True and time() - self.time > self.wait_time:
                sublime.set_timeout(lambda: self.payload(), 0)
            sleep(0.5)


###########################
# Plugin Initialization
###########################
def init_css():
    """ Load up desired CSS """
    global css
    global border_color
    global back_arrow
    global cross

    scheme_file = pref_settings.get('color_scheme')
    try:
        lums = scheme_lums(scheme_file)
    except:
        lums = 128

    if lums <= 127:
        css_file = 'Packages/' + ch_settings.get(
            'dark_css_override',
            'ColorHelper/css/dark.css'
        )
        border_color = '#CCCCCC'
        cross = 'res://Packages/ColorHelper/res/cross_dark.png'
        back_arrow = 'res://Packages/ColorHelper/res/back_dark.png'
    else:
        css_file = 'Packages/' + ch_settings.get(
            'light_css_override',
            'ColorHelper/css/light.css'
        )
        border_color = '#333333'
        cross = 'res://Packages/ColorHelper/res/cross_light.png'
        back_arrow = 'res://Packages/ColorHelper/res/back_light.png'

    try:
        css = sublime.load_resource(css_file).replace('\r', '\n')
    except:
        css = None
    ch_settings.clear_on_change('reload')
    ch_settings.add_on_change('reload', init_css)


def init_color_scheme():
    """ Setup color scheme match object with current scheme """
    global pref_settings
    global scheme_matcher
    pref_settings = sublime.load_settings('Preferences.sublime-settings')
    pref_settings.clear_on_change('reload')
    pref_settings.add_on_change('reload', init_color_scheme)

    # Reload the CSS since it can change with scheme luminance
    init_css()


def init_plugin():
    """ Setup plugin variables and objects """
    global ch_settings
    global ch_thread

    # Setup settings
    ch_settings = sublime.load_settings('color_helper.sublime-settings')

    # Setup color scheme
    init_color_scheme()

    if ch_thread is not None:
        ch_thread.kill()
    ch_thread = ChThread()
    ch_thread.start()


def plugin_loaded():
    """ Setup plugin """
    init_plugin()


def plugin_unloaded():
    ch_thread.kill()
