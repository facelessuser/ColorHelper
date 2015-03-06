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
import os

css = None
pref_settings = None
ch_settings = None
border_color = '#333333'
back_arrow = None
cross = None
bookmark = None
bookmark_selected = None
dropper = None
color_palette = None


FLOAT_TRIM_RE = re.compile(r'^(?P<keep>\d+)(?P<trash>\.0+|(?P<keep2>\.\d*[1-9])0+)$')

HEX_RE = re.compile(r'^(?P<hex>\#(?P<hex_content>(?:[\dA-Fa-f]{3}){1,2}))$')

COMPLETE = r'''(?x)
    (?P<hex>\#(?P<hex_content>(?:[\dA-Fa-f]{3}){1,2})) |
    (?P<rgb>rgb\(\s*(?P<rgb_content>(?:\d+\s*,\s*){2}\d+)\s*\)) |
    (?P<rgba>rgba\(\s*(?P<rgba_content>(?:\d+\s*,\s*){3}(?:(?:\d*\.\d+)|\d))\s*\)) |
    (?P<hsl>hsl\(\s*(?P<hsl_content>\d+\s*,\s*(?:(?:\d*\.\d+)|\d)%\s*,\s*(?:(?:\d*\.\d+)|\d)%)\s*\)) |
    (?P<hsla>hsla\(\s*(?P<hsla_content>\d+\s*,\s*(?:(?:(?:\d*\.\d+)|\d)%\s*,\s*){2}(?:(?:\d*\.\d+)|\d))\s*\))'''

INCOMPLETE = r''' |
    (?P<hash>\#) |
    (?P<rgb_open>rgb\() |
    (?P<rgba_open>rgba\() |
    (?P<hsl_open>hsl\() |
    (?P<hsla_open>hsla\()'''

COLOR_RE = re.compile(COMPLETE)

COLOR_ALL_RE = re.compile(COMPLETE + INCOMPLETE)

if 'ch_thread' not in globals():
    ch_thread = None

if 'ch_file_thread' not in globals():
    ch_file_thread = None


###########################
# Helper Classes/Functions
###########################
def log(*args):
    text = ['\nColorHelper: ']
    for arg in args:
        text.append(str(arg))
    text.append('\n')
    print(''.join(text))


def debug(*args):
    if sublime.load_settings("color_helper.sublime-settings").get('debug', False):
        log(*args)


def fmt_float(f, p=0):
    """ Set float pring precision and trim precision zeros """
    string = ("%." + "%d" % p + "f") % f
    m = FLOAT_TRIM_RE.match(string)
    if m:
        string = m.group('keep')
        if m.group('keep2'):
            string += m.group('keep2')
    return string


def is_hex_color(color):
    return color is not None and HEX_RE.match(color) is not None


def get_theme_res(tt_theme, *args):
    return '/'.join(('Packages', tt_theme) + args)


def get_scope(view):
    file_scope = None
    syntax = view.settings().get('syntax')
    language = os.path.basename(syntax).replace('.tmLanguage', '').lower() if syntax is not None else "plain text"
    supported = ch_settings.get('supported_syntax', {"CSS": "meta.property-value.css -comment"})
    for lang, scope in supported.items():
        if lang.lower() == language:
            file_scope = scope
            break
    return file_scope


def get_favs():
    bookmark_colors = sublime.load_settings('color_helper.palettes').get("favorites", [])
    return {"name": "Favorites", "colors": bookmark_colors}


def get_palettes():
    return sublime.load_settings('color_helper.palettes').get("palettes", [])


def start_file_index(view):
    if not ch_file_thread.busy:
        scope = get_scope(view)
        if scope is not None:
            source = []
            for r in view.find_by_selector(scope):
                source.append(view.substr(r))
            debug('Regions to search:\n', source)
            ch_file_thread.set_index(view, ''.join(source))
            sublime.status_message('File color indexer started...')


class InsertionCalc(object):
    def __init__(self, view, point, target_color):
        """ Init insertion object """
        self.view = view
        self.convert_rgb = False
        self.convert_hsl = False
        self.alpha = None
        self.region = sublime.Region(point)
        self.format_override = False
        self.start = point - 50
        self.end = point + 50
        self.point = point
        visible = self.view.visible_region()
        if self.start < visible.begin():
            self.start = visible.begin()
        if self.end > visible.end():
            self.end = visible.end()
        self.use_web_colors = bool(ch_settings.get('use_webcolor_names', True))
        self.preferred_format = ch_settings.get('preferred_format', 'hex')
        self.preferred_alpha_format = ch_settings.get('preferred_alpha_format', 'rgba')
        self.target_color = target_color
        try:
            self.web_color = webcolors.hex_to_name(target_color) if self.use_web_colors else None
        except:
            self.web_color = None

    def replacement(self, m):
        """ See if match is a replacement of an existing color """
        found = True
        if m.group('hex'):
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
            if self.preferred_format in ('rgb', 'hsl'):
                self.format_override = True
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
                else:
                    self.convert_hsl = True
        elif m.group('rgb'):
            if self.web_color:
                self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
            else:
                if self.preferred_format in ('hex', 'hsl'):
                    self.format_override = True
                    self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
                    if self.preferred_format == 'hsl':
                        self.convert_hsl = True
                else:
                    self.region = sublime.Region(m.start('rgb_content') + self.start, m.end('rgb_content') + self.start)
                    self.convert_rgb = True
        elif m.group('rgba'):
            self.web_color = None
            if self.preferred_alpha_format == 'hsla':
                self.format_override = True
                self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
                self.convert_hsl = True
            else:
                self.region = sublime.Region(m.start('rgba_content') + self.start, m.end('rgba_content') + self.start)
                self.convert_rgb = True
            content = [x.strip() for x in m.group('rgba_content').split(',')]
            self.alpha = content[3]
        elif m.group('hsl'):
            if self.web_color:
                self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
            else:
                if self.preferred_format in ('hex', 'rgb'):
                    self.format_override = True
                    self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
                    if self.preferred_format == 'rgb':
                        self.convert_rgb = True
                self.region = sublime.Region(m.start('hsl_content') + self.start, m.end('hsl_content') + self.start)
                self.convert_hsl = True
        elif m.group('hsla'):
            self.web_color = None
            if self.preferred_alpha_format == 'rgba':
                self.format_override = True
                self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
                self.convert_rgb = True
            else:
                self.region = sublime.Region(m.start('hsla_content') + self.start, m.end('hsla_content') + self.start)
                self.convert_hsl = True
            content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
            self.alpha = content[3]
        else:
            found = False
        return found

    def completion(self, m):
        """ See if match is completing an color """
        found = False
        if m.group('hash'):
            self.region = sublime.Region(m.start('hash') + self.start, m.end('hash') + self.start)
            if self.preferred_format in ('rgb', 'hsl'):
                self.format_override = True
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
                else:
                    self.convert_hsl = True
        elif m.group('rgb_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.web_color:
                self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
            elif self.preferred_format in ('hex', 'hsl'):
                    self.format_override = True
                    self.region = sublime.Region(m.start('rgb_open') + self.start, m.end('rgb_open') + self.start + offset)
                    if self.preferred_format == 'hsl':
                        self.convert_hsl = True
            else:
                self.convert_rgb = True
        elif m.group('rgba_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.preferred_alpha_format == 'hsla':
                self.format_override = True
                self.region = sublime.Region(m.start('rgba_open') + self.start, m.end('rgb_open') + self.start + offset)
                self.convert_hsl = True
            else:
                self.convert_rgb = True
            self.alpha = '1'
        elif m.group('hsl_open'):
            offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.web_color:
                self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
            elif self.preferred_format in ('hex', 'rgb'):
                self.format_override = True
                self.region = sublime.Region(m.start('hsl_open') + self.start, m.end('hsl_open') + self.start + offset)
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
            else:
                self.convert_hsl = True
        elif m.group('hsla_open'):
            self.offset = 1 if self.view.substr(self.point) == ')' else 0
            if self.preferred_alpha_format == 'rgba':
                self.format_override = True
                self.region = sublime.Region(m.start('hsla_open') + self.start, m.end('hsla_open') + self.start + offset)
                self.convert_rgb = True
            else:
                self.convert_hsl = True
            self.alpha = '1'
        else:
            found = False
        return found

    def calc(self):
        """ Calculate how we are to insert the target_color """
        bfr = self.view.substr(sublime.Region(self.start, self.end))
        ref = self.point - self.start
        found = False
        for m in COLOR_ALL_RE.finditer(bfr):
            if ref >= m.start(0) and ref < m.end(0):
                found = self.replacement(m)
            elif ref == m.end(0):
                found = self.completion(m)
            if found:
                break

        if not found:
            word_region = self.view.word(sublime.Region(self.point))
            word = self.view.substr(word_region)
            try:
                webcolors.name_to_hex(word)
                self.region = word_region
            except:
                pass
        return found


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
        elif href.startswith('__color_picker__'):
            color = href.split(':')[1]
            s = sublime.load_settings('color_helper_share.sublime-settings')
            s.set('color_pick_return', None)
            self.view.window().run_command(
                'color_pick_api_get_color',
                {'settings': 'color_helper_share.sublime-settings', "default_color": color[1:]}
            )
            new_color = s.get('color_pick_return', None)
            if new_color is not None and new_color != color:
                self.insert_color(new_color)
            else:
                sublime.set_timeout(self.show_color_info, 0)
        elif href.startswith('__add_fav__'):
            color = href.split(':')[1]
            favs = get_favs()
            favs['colors'].append(color)
            settings = sublime.load_settings('color_helper.palettes')
            settings.set('favorites', favs['colors'])
            sublime.save_settings('color_helper.palettes')
            self.show_color_info(update=True)
        elif href.startswith('__remove_fav__'):
            color = href.split(':')[1]
            favs = get_favs()
            favs['colors'].remove(color)
            settings = sublime.load_settings('color_helper.palettes')
            settings.set('favorites', favs['colors'])
            sublime.save_settings('color_helper.palettes')
            self.show_color_info(update=True)

    def insert_color(self, target_color):
        """ Insert colors """
        sels = self.view.sel()
        if (len(sels) == 1 and sels[0].size() == 0):
            point = sels[0].begin()
            insert_calc = InsertionCalc(self.view, point, target_color)
            insert_calc.calc()
            if insert_calc.web_color:
                value = insert_calc.web_color
            elif insert_calc.convert_rgb:
                value = "%d, %d, %d" % (
                    int(target_color[1:3], 16),
                    int(target_color[3:5], 16),
                    int(target_color[5:7], 16)
                )
                if insert_calc.alpha:
                    value += ', %s' % insert_calc.alpha
                if insert_calc.format_override:
                    value = ("rgba(%s)" if insert_calc.alpha else "rgb(%s)") % value
            elif insert_calc.convert_hsl:
                hsl = RGBA(target_color)
                h, l, s = hsl.tohls()
                value = "%s, %s%%, %s%%" % (
                    fmt_float(h * 360.0),
                    fmt_float(s * 100.0),
                    fmt_float(l * 100.0)
                )
                if insert_calc.alpha:
                    value += ', %s' % insert_calc.alpha
                if insert_calc.format_override:
                    value = ("hsla(%s)" if insert_calc.alpha else "hsl(%s)") % value
            else:
                use_upper = ch_settings.get("upper_case_hex", False)
                value = target_color.upper() if use_upper else target_color.lower()
            self.view.sel().subtract(sels[0])
            self.view.sel().add(insert_calc.region)
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

        info.append(
            color_box(color, border_color, size=64)
        )

        info.append(
            ' <a href="__palettes__">' +
            '<img style="width: 20px; height: 20px;" src="%s">' % color_palette +
            '</a>'
        )

        s = sublime.load_settings('color_helper_share.sublime-settings')
        s.set('color_pick_return', None)
        sublime.run_command('color_pick_api_is_available', {'settings': 'color_helper_share.sublime-settings'})
        if s.get('color_pick_return', None):
            info.append(
                '<a href="__color_picker__:%s"><img style="width: 16px; height: 16px;" src="%s"></a>' % (color, dropper)
            )

        if color in get_favs()['colors']:
            info.append(
                '<a href="__remove_fav__:%s">' % color.lower() +
                '<img style="width: 20px; height: 20px;" src="%s">' % bookmark_selected +
                '</a>'
            )
        else:
            info.append(
                '<a href="__add_fav__:%s">' % color.lower() +
                '<img style="width: 20px; height: 20px;" src="%s">' % bookmark +
                '</a>'
            )
        info.append('<br><br>')
        info.append(
            '<span class="key">r:</span> %d ' % rgba.r +
            '<span class="key">g:</span> %d ' % rgba.g +
            '<span class="key">b:</span> %d<br>' % rgba.b
        )
        h, l, s = rgba.tohls()
        info.append(
            '<span class="key">h:</span> %s ' % fmt_float(h * 360.0) +
            '<span class="key">s:</span> %s%% ' % fmt_float(s * 100.0) +
            '<span class="key">l:</span> %s%%<br>' % fmt_float(l * 100.0)
        )
        h, s, v = rgba.tohsv()
        info.append(
            '<span class="key">h:</span> %s ' % fmt_float(h * 360.0) +
            '<span class="key">s:</span> %s%% ' % fmt_float(s * 100.0) +
            '<span class="key">v:</span> %s%%<br>' % fmt_float(v * 100.0)
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
            html.append('<a href="__info__"><img style="width: 20px; height: 20px;" src="%s"></a>' % back_arrow)

        favs = get_favs()
        palettes = []
        if len(favs['colors']):
            palettes += [favs]

        current_colors = self.view.settings().get('color_helper_file_palette', [])
        if len(current_colors):
            palettes += [{"name": "Current Colors", "colors": current_colors}]

        for palette in (palettes + get_palettes()):
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
        if palette_name == "Current Colors":
            target = {
                "name": "Current Colors",
                "colors": self.view.settings().get('color_helper_file_palette', [])
            }
        elif palette_name == "Favorites":
            target = get_favs()

        for palette in get_palettes():
            if palette_name == palette['name']:
                target = palette

        if target is not None:
            html = [
                '<style>%s</style>' % (css if css is not None else '') +
                '<div class="content">' +
                '<a href="__palettes__"><img style="width: 20px; height: 20px;" src="%s"></a>' % back_arrow +
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
                            color = "#%02x%02x%02x" % (
                                int(content[0:2], 16), int(content[2:4], 16), int(content[4:6], 16)
                            )
                        else:
                            color = "#%02x%02x%02x" % (
                                int(content[0:1] * 2, 16), int(content[1:2] * 2, 16), int(content[2:3] * 2, 16)
                            )
                        break
                    elif m.group('rgb'):
                        content = [x.strip() for x in m.group('rgb_content').split(',')]
                        color = "#%02x%02x%02x" % (
                            int(content[0]), int(content[1]), int(content[2])
                        )
                        break
                    elif m.group('rgba'):
                        content = [x.strip() for x in m.group('rgba_content').split(',')]
                        color = "#%02x%02x%02x%02x" % (
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
                        color = rgba.get_rgb()
                        break
                    elif m.group('hsla'):
                        content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
                        rgba = RGBA()
                        h = float(content[0]) / 360.0
                        s = float(content[1]) / 100.0
                        l = float(content[2]) / 100.0
                        rgba.fromhls(h, l, s)
                        color = rgba.get_rgb()
                        color += "%02X" % int('%.0f' % (float(content[3]) * 255.0))
                        break
            if color is None:
                word = self.view.substr(self.view.word(sels[0]))
                try:
                    color = webcolors.name_to_hex(word).lower()
                except:
                    pass
        if color is not None:
            html = [
                '<style>%s</style>' % (css if css is not None else '') +
                '<div class="content">'
            ]

            html.append(
                # '<br>' +
                self.format_info(color.lower()) +
                '</div>'
            )

            if update:
                self.view.update_popup(''.join(html))
            else:
                self.view.show_popup(
                    ''.join(html), location=-1, max_width=600,
                    on_navigate=self.on_navigate
                )
        elif update:
            self.view.hide_popup()

    def run(self, edit, mode="palette", palette_name=None, color=None):
        """ Run the specified tooltip """
        self.no_info = True
        if mode == "palette":
            if palette_name is not None:
                self.show_colors(palette_name)
            else:
                self.show_palettes()
        elif mode == "color" and is_hex_color(color):
            self.insert_color(color)
        elif mode == "info":
            self.no_info = False
            self.show_color_info()


class ColorHelperFileIndexCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        busy = False
        if get_scope(self.view) is not None:
            count = 0
            while ch_file_thread.busy:
                if count == 3:
                    sublime.error_message("File indexer is busy!")
                    busy = True
                    break
                sleep(1)
                count += 1
            if not busy:
                start_file_index(self.view)
        else:
            sublime.error_message('Cannot index colors in this file!')


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

    on_modified = on_selection_modified

    def on_activated(self, view):
        if view.settings().get('color_helper_file_palette', None) is None:
            view.settings().set('color_helper_file_palette', [])
            self.on_index(view)

    def on_index(self, view):
        start_file_index(view)

    on_post_save = on_index
    on_clone = on_index


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
            scope = get_scope(view)
            if (
                scope is not None and
                len(sels) == 1 and sels[0].size() == 0
                and view.score_selector(sels[0].begin(), scope)
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
                for m in COLOR_ALL_RE.finditer(bfr):
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
                    region = view.word(sels[0])
                    word = view.substr(view.word(sels[0]))
                    if point != region.end():
                        try:
                            webcolors.name_to_hex(word)
                            execute = True
                            info = True
                        except:
                            pass
                if execute:
                    view.run_command('color_helper', {"mode": "palette" if not info else "info"})
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


class ChFileIndexThread(threading.Thread):
    """ Load up defaults """

    def __init__(self):
        """ Setup the thread """
        self.reset()
        self.lock = threading.Lock()
        self.webcolor_names = re.compile(
            r'\b(%s)\b' % '|'.join(
                [name for name in webcolors.css3_names_to_hex.keys()]
            )
        )
        threading.Thread.__init__(self)

    def reset(self):
        """ Reset the thread variables """
        self.abort = False
        self.view = None
        self.source = ''
        self.busy = False

    def update_index(self, view, colors):
        """ Code to run """
        try:
            sublime.status_message('File color index complete...')
            view.settings().set('color_helper_file_palette', colors)
            debug('Colors:\n', colors)
        except Exception as e:
            debug(e)
            pass

    def set_index(self, view, source):
        with self.lock:
            self.view = view
            self.source = source

    def kill(self):
        """ Kill thread """
        self.abort = True
        while self.is_alive():
            pass
        self.reset()

    def run(self):
        """ Thread loop """
        while not self.abort:
            sleep(0.5)
            with self.lock:
                if self.source:
                    self.busy = True
                    self.index_colors()
                    if not self.abort:
                        self.reset()

    def index_colors(self):
        colors = set()
        for m in COLOR_RE.finditer(self.source):
            if self.abort:
                break
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
            elif m.group('rgb'):
                content = [x.strip() for x in m.group('rgb_content').split(',')]
                color = "%02x%02x%02x" % (
                    int(content[0]), int(content[1]), int(content[2])
                )
            elif m.group('rgba'):
                content = [x.strip() for x in m.group('rgba_content').split(',')]
                color = "%02x%02x%02x" % (
                    int(content[0]), int(content[1]), int(content[2])
                )
            elif m.group('hsl'):
                content = [x.strip().rstrip('%') for x in m.group('hsl_content').split(',')]
                rgba = RGBA()
                h = float(content[0]) / 360.0
                s = float(content[1]) / 100.0
                l = float(content[2]) / 100.0
                rgba.fromhls(h, l, s)
                color = rgba.get_rgb()[1:]
            elif m.group('hsla'):
                content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
                rgba = RGBA()
                h = float(content[0]) / 360.0
                s = float(content[1]) / 100.0
                l = float(content[2]) / 100.0
                rgba.fromhls(h, l, s)
                color = rgba.get_rgb()[1:]
            if color is not None:
                colors.add('#' + color)
        for m in self.webcolor_names.finditer(self.source):
            if self.abort:
                break
            colors.add(webcolors.name_to_hex(m.group(0)))
        if not self.abort:
            sublime.set_timeout(
                lambda view=self.view, colors=list(colors): self.update_index(view, colors), 0
            )


###########################
# Plugin Initialization
###########################
def init_css():
    """ Load up desired CSS """
    global css
    global border_color
    global back_arrow
    global cross
    global bookmark
    global bookmark_selected
    global dropper
    global color_palette

    scheme_file = pref_settings.get('color_scheme')
    try:
        lums = scheme_lums(scheme_file)
    except:
        lums = 128

    tt_theme = ch_settings.get('tooltip_theme', 'ColorHelper/tt_theme')

    if lums <= 127:
        border_color = '#CCCCCC'
        css_file = get_theme_res(tt_theme, 'css', 'dark.css')
        cross = 'res://' + get_theme_res(tt_theme, 'images', 'cross_dark.png')
        back_arrow = 'res://' + get_theme_res(tt_theme, 'images', 'back_dark.png')
        bookmark = 'res://' + get_theme_res(tt_theme, 'images', 'bookmark_dark.png')
        bookmark_selected = 'res://' + get_theme_res(tt_theme, 'images', 'bookmark_selected_dark.png')
        dropper = 'res://' + get_theme_res(tt_theme, 'images', 'dropper_dark.png')
        color_palette = 'res://' + get_theme_res(tt_theme, 'images', 'palette_dark.png')
    else:
        border_color = '#333333'
        css_file = get_theme_res(tt_theme, 'css', 'light.css')
        cross = 'res://' + get_theme_res(tt_theme, 'images', 'cross_light.png')
        back_arrow = 'res://' + get_theme_res(tt_theme, 'images', 'back_light.png')
        bookmark = 'res://' + get_theme_res(tt_theme, 'images', 'bookmark_light.png')
        bookmark_selected = 'res://' + get_theme_res(tt_theme, 'images', 'bookmark_selected_light.png')
        dropper = 'res://' + get_theme_res(tt_theme, 'images', 'dropper_light.png')
        color_palette = 'res://' + get_theme_res(tt_theme, 'images', 'palette_light.png')

    try:
        css = sublime.load_resource(css_file).replace('\r', '')
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
    global ch_file_thread

    # Setup settings
    ch_settings = sublime.load_settings('color_helper.sublime-settings')

    # Setup color scheme
    init_color_scheme()

    if ch_thread is not None:
        ch_thread.kill()
    ch_thread = ChThread()
    ch_thread.start()

    if ch_file_thread is not None:
        ch_file_thread.kill()
    ch_file_thread = ChFileIndexThread()
    ch_file_thread.start()


def plugin_loaded():
    """ Setup plugin """
    init_plugin()


def plugin_unloaded():
    ch_thread.kill()
    ch_file_thread.kill()
