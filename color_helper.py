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
from ColorHelper.lib.ase import loads as ase_load
import ColorHelper.lib.webcolors as webcolors
import threading
from time import time, sleep
import re
import os
import codecs
import json
import traceback


FLOAT_TRIM_RE = re.compile(r'^(?P<keep>\d+)(?P<trash>\.0+|(?P<keep2>\.\d*[1-9])0+)$')

HEX_RE = re.compile(r'^(?P<hex>\#(?P<hex_content>(?:[\dA-Fa-f]{3}){1,2}))$')

COMPLETE = r'''(?x)
    (?P<hex>\#(?P<hex_content>(?:[\dA-Fa-f]{3}){1,2}))\b |
    \b(?P<rgb>rgb\(\s*(?P<rgb_content>(?:\d+\s*,\s*){2}\d+)\s*\)) |
    \b(?P<rgba>rgba\(\s*(?P<rgba_content>(?:\d+\s*,\s*){3}(?:(?:\d*\.\d+)|\d))\s*\)) |
    \b(?P<hsl>hsl\(\s*(?P<hsl_content>\d+\s*,\s*(?:(?:\d*\.\d+)|\d+)%\s*,\s*(?:(?:\d*\.\d+)|\d+)%)\s*\)) |
    \b(?P<hsla>hsla\(\s*(?P<hsla_content>\d+\s*,\s*(?:(?:(?:\d*\.\d+)|\d+)%\s*,\s*){2}(?:(?:\d*\.\d+)|\d))\s*\))'''

INCOMPLETE = r''' |
    (?P<hash>\#) |
    \b(?P<rgb_open>rgb\() |
    \b(?P<rgba_open>rgba\() |
    \b(?P<hsl_open>hsl\() |
    \b(?P<hsla_open>hsla\()'''

COLOR_NAMES = r'| (?i)\b(?P<webcolors>%s)\b' % '|'.join([name for name in webcolors.css3_names_to_hex.keys()])

TAG_HTML_RE = re.compile(
    br'''(?x)(?i)
    (?:
        (?P<comments>(\r?\n?\s*)<!--[\s\S]*?-->(\s*)(?=\r?\n)|<!--[\s\S]*?-->)|
        (?P<style><style((?:\s+[\w\-:]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^>\s]+))?)*)\s*>(?P<css>.*?)<\/style[^>]*>) |
        (?P<open><[\w\:\.\-]+)
        (?P<attr>(?:\s+[\w\-:]+(?:\s*=\s*(?:"[^"]*"|'[^']*'))?)*)
        (?P<close>\s*(?:\/?)>)
    )
    ''',
    re.DOTALL
)

TAG_STYLE_ATTR_RE = re.compile(
    br'''(?x)
    (?P<attr>
        (?:
            \s+style
            (?:\s*=\s*(?P<content>"[^"]*"|'[^']*'))
        )
    )
    ''',
    re.DOTALL
)

COLOR_RE = re.compile(r'(?!<[@#$.\-_])(?:%s%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES))

COLOR_ALL_RE = re.compile(r'(?!<[@#$.\-_])(?:%s%s%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES, INCOMPLETE))

INDEX_ALL_RE = re.compile((r'(?!<[@#$.\-_])(?:%s%s)(?![@#$.\-_])' % (COMPLETE, COLOR_NAMES)).encode('utf-8'))

ch_theme = None
ch_settings = None

if 'ch_thread' not in globals():
    ch_thread = None

if 'ch_file_thread' not in globals():
    ch_file_thread = None

if 'ch_project_thread' not in globals():
    ch_project_thread = None


###########################
# Helper Classes/Functions
###########################
def log(*args):
    """ Log """
    text = ['\nColorHelper: ']
    for arg in args:
        text.append(str(arg))
    text.append('\n')
    print(''.join(text))


def debug(*args):
    """ Log if debug enabled """
    if sublime.load_settings("color_helper.sublime-settings").get('debug', False):
        log(*args)


def get_cache_dir():
    """ Get the cache dir """
    return os.path.join(sublime.packages_path(), "User", 'ColorHelper.cache')


def color_picker_available():
    """ Check if color picker is available """
    s = sublime.load_settings('color_helper_share.sublime-settings')
    s.set('color_pick_return', None)
    sublime.run_command('color_pick_api_is_available', {'settings': 'color_helper_share.sublime-settings'})
    return s.get('color_pick_return', None)


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
    """ Is color a hex color """
    return color is not None and HEX_RE.match(color) is not None


def get_scope(view, skip_sel_check=False):
    """ Get auto-popup scope rule """
    scopes = ','.join(ch_settings.get('supported_syntax', []))
    sels = view.sel()
    if not skip_sel_check:
        if len(sels) == 0 or not scopes or view.score_selector(sels[0].begin(), scopes) == 0:
            scopes = None
    return scopes


def get_favs():
    """ Get favorites object """
    bookmark_colors = sublime.load_settings('color_helper.palettes').get("favorites", [])
    return {"name": "Favorites", "colors": bookmark_colors}


def save_palettes(palettes, favs=False):
    """ Save palettes """
    s = sublime.load_settings('color_helper.palettes')
    if favs:
        s.set('favorites', palettes)
    else:
        s.set('palettes', palettes)
    sublime.save_settings('color_helper.palettes')


def save_project_palettes(window, palettes):
    """ Save project palettes """
    data = window.project_data()
    if data is None:
        data = {'color_helper_palettes': palettes}
    else:
        data['color_helper_palettes'] = palettes
    window.set_project_data(data)


def get_palettes():
    """ Get palettes """
    return sublime.load_settings('color_helper.palettes').get("palettes", [])


def get_project_palettes(window):
    """ Get project palettes """
    data = window.project_data()
    if data is None:
        data = {}
    return data.get('color_helper_palettes', [])


def get_project_folders(window):
    """ Get project folder """
    data = window.project_data()
    if data is None:
        data = {'folders': [{'path': f} for f in window.folders()]}
    return data.get('folders', [])


def start_file_index(view):
    """ Kick off current file color index """
    global ch_file_thread
    if view is not None and (ch_file_thread is None or not ch_file_thread.is_alive()):
        scope = get_scope(view, skip_sel_check=True)
        if scope:
            source = []
            for r in view.find_by_selector(scope):
                source.append(view.substr(r))
            debug('Regions to search:\n', source)
            if len(source):
                ch_file_thread = ChFileIndexThread(view, ' '.join(source))
                ch_file_thread.start()
                sublime.status_message('File color indexer started...')


def translate_color(m):
    # Translate the match object to a color w/ alpha
    color = None
    alpha = None
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
    elif m.group('rgb'):
        content = [x.strip() for x in m.group('rgb_content').split(',')]
        color = "#%02x%02x%02x" % (
            int(content[0]), int(content[1]), int(content[2])
        )
    elif m.group('rgba'):
        content = [x.strip() for x in m.group('rgba_content').split(',')]
        color = "#%02x%02x%02x" % (
            int(content[0]), int(content[1]), int(content[2])
        )
        alpha = content[3]
    elif m.group('hsl'):
        content = [x.strip().rstrip('%') for x in m.group('hsl_content').split(',')]
        rgba = RGBA()
        h = float(content[0]) / 360.0
        s = float(content[1]) / 100.0
        l = float(content[2]) / 100.0
        rgba.fromhls(h, l, s)
        color = rgba.get_rgb()
    elif m.group('hsla'):
        content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
        rgba = RGBA()
        h = float(content[0]) / 360.0
        s = float(content[1]) / 100.0
        l = float(content[2]) / 100.0
        rgba.fromhls(h, l, s)
        color = rgba.get_rgb()
        alpha = content[3]
    elif m.group('webcolors'):
        try:
            color = webcolors.name_to_hex(m.group('webcolors')).lower()
        except:
            pass
    return color, alpha


class InsertionCalc(object):
    def __init__(self, view, point, target_color, convert=None):
        """ Init insertion object """
        self.convert = '' if convert is None else convert
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
        self.force_alpha = False
        if self.convert:
            self.format_override = True
            if self.convert == "name":
                self.use_web_colors = True
                if len(target_color) > 7:
                    target_color = target_color[:-2]
            elif self.convert == 'hex':
                self.convert_rgb = False
                self.use_web_colors = False
            elif self.convert in ('rgb', 'rgba'):
                self.convert_rgb = True
                self.force_alpha = self.convert == 'rgba'
                self.use_web_colors = False
            elif self.convert in ('hsl', 'hsla'):
                self.convert_hsl = True
                self.force_alpha = self.convert == 'hsla'
                self.use_web_colors = False

        self.target_color = target_color
        try:
            self.web_color = webcolors.hex_to_name(target_color) if self.use_web_colors else None
        except:
            self.web_color = None

    def replacement(self, m):
        """ See if match is a replacement of an existing color """
        found = True
        if m.group('webcolors'):
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
            if self.preferred_format in ('rgb', 'hsl'):
                self.format_override = True
                if self.preferred_format == 'rgb':
                    self.convert_rgb = True
                else:
                    self.convert_hsl = True
        elif m.group('hex'):
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
                if self.preferred_format in ('hex', 'hsl') or self.convert:
                    self.format_override = True
                    self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
                    if self.preferred_format == 'hsl':
                        self.convert_hsl = True
                else:
                    self.region = sublime.Region(m.start('rgb_content') + self.start, m.end('rgb_content') + self.start)
                    self.convert_rgb = True
        elif m.group('rgba'):
            self.web_color = None
            if self.preferred_alpha_format == 'hsla' or self.convert:
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
                if self.preferred_format in ('hex', 'rgb') or self.convert:
                    self.format_override = True
                    self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
                    if self.preferred_format == 'rgb':
                        self.convert_rgb = True
                else:
                    self.region = sublime.Region(m.start('hsl_content') + self.start, m.end('hsl_content') + self.start)
                    self.convert_hsl = True
        elif m.group('hsla'):
            self.web_color = None
            if self.preferred_alpha_format == 'rgba' or self.convert:
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

    def converting(self, m):
        """ See if match is a convert replacement of an existing color """
        found = True
        if m.group('webcolors'):
            self.region = sublime.Region(m.start('webcolors') + self.start, m.end('webcolors') + self.start)
        elif m.group('hex'):
            self.region = sublime.Region(m.start('hex') + self.start, m.end('hex') + self.start)
        elif m.group('rgb'):
            self.region = sublime.Region(m.start('rgb') + self.start, m.end('rgb') + self.start)
        elif m.group('rgba'):
            self.region = sublime.Region(m.start('rgba') + self.start, m.end('rgba') + self.start)
            content = [x.strip() for x in m.group('rgba_content').split(',')]
            self.alpha = content[3]
        elif m.group('hsl'):
            self.region = sublime.Region(m.start('hsl') + self.start, m.end('hsl') + self.start)
        elif m.group('hsla'):
            self.region = sublime.Region(m.start('hsla') + self.start, m.end('hsla') + self.start)
            content = [x.strip().rstrip('%') for x in m.group('hsla_content').split(',')]
            self.alpha = content[3]
        else:
            found = False
        return found

    def convert_alpha(self):
        """ Setup conversion alpha """
        if self.force_alpha and self.alpha is None:
            self.alpha = '1'
        elif not self.force_alpha:
            self.alpha = None

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
            if self.convert:
                if ref >= m.start(0) and ref < m.end(0):
                    found = self.converting(m)
                elif ref < m.start(0):
                    break
            elif ref >= m.start(0) and ref < m.end(0):
                found = self.replacement(m)
            elif ref == m.end(0):
                found = self.completion(m)
            elif ref > m.end(0):
                break
            if found:
                break

        if self.convert:
            self.convert_alpha()

        return found


###########################
# Main Code
###########################
class ColorHelperCommand(sublime_plugin.TextCommand):
    def on_navigate(self, href):
        """ Handle link clicks """
        if href.startswith('#'):
            self.insert_color(href)
        elif href.startswith('__colors__'):
            parts = href.split(':', 2)
            self.show_colors(parts[1], parts[2], update=True)
        elif href == '__close__':
            self.view.hide_popup()
        elif href == '__palettes__':
            self.show_palettes(update=True)
        elif href == '__info__':
            self.show_color_info(update=True)
        elif href.startswith('__color_picker__'):
            self.color_picker(color=href.split(':', 1)[1])
        elif href.startswith('__add_fav__'):
            self.add_fav(href.split(':', 1)[1])
        elif href.startswith('__remove_fav__'):
            self.remove_fav(href.split(':', 1)[1])
        elif href.startswith('__delete_colors__'):
            parts = href.split(':', 2)
            self.show_colors(parts[1], parts[2], delete=True, update=True)
        elif href.startswith('__delete_color__'):
            parts = href.split(':', 3)
            self.delete_color(parts[1], parts[2], parts[3])
        elif href == '__delete__palettes__':
            self.show_palettes(delete=True, update=True)
        elif href.startswith('__delete__palette__'):
            parts = href.split(':', 2)
            self.delete_palette(parts[1], parts[2])
        elif href.startswith('__add_color__'):
            self.show_palettes(color=href.split(':', 1)[1], update=True)
        elif href.startswith('__add_palette_color__'):
            parts = href.split(':', 3)
            self.add_palette(parts[1], parts[2], parts[3])
        elif href.startswith('__create_palette__'):
            parts = href.split(':', 2)
            self.prompt_palette_name(parts[1], parts[2])
        elif href.startswith('__convert__'):
            parts = href.split(':', 2)
            self.insert_color(parts[1], parts[2])

    def repop(self):
        """ Setup thread to repopup tooltip """
        return
        if ch_thread.ignore_all:
            return
        now = time()
        ch_thread.modified = True
        ch_thread.time = now

    def prompt_palette_name(self, palette_type, color):
        """ Prompt user for new palette name """
        win = self.view.window()
        if win is not None:
            self.view.hide_popup()
            win.show_input_panel(
                "Palette Name:", '',
                on_done=lambda name, t=palette_type, c=color: self.create_palette(name, t, color),
                on_change=None,
                on_cancel=self.repop
            )

    def create_palette(self, palette_name, palette_type, color):
        """ Add color to new color palette """
        if palette_type == '__global__':
            color_palettes = get_palettes()
            for palette in color_palettes:
                if palette_name == palette['name']:
                    sublime.error_message('The name of "%s" is already in use!')
                    return
            color_palettes.append({"name": palette_name, 'colors': [color]})
            save_palettes(color_palettes)
        elif palette_type == '__project__':
            color_palettes = get_project_palettes(self.view.window())
            for palette in color_palettes:
                if palette_name == palette['name']:
                    sublime.error_message('The name of "%s" is already in use!')
                    return
            color_palettes.append({"name": palette_name, 'colors': [color]})
            save_project_palettes(self.view.window(), color_palettes)
        self.repop()

    def add_palette(self, color, palette_type, palette_name):
        """ Add pallete """
        if palette_type == "__special__":
            if palette_name == 'Favorites':
                favs = get_favs()['colors']
                if color not in favs:
                    favs.append(color)
                save_palettes(favs, favs=True)
                self.show_color_info(update=True)
        elif palette_type in ('__global__', '__project__'):
            if palette_type == '__global__':
                color_palettes = get_palettes()
            else:
                color_palettes = get_project_palettes(self.view.window())
            for palette in color_palettes:
                if palette_name == palette['name']:
                    if color not in palette['colors']:
                        palette['colors'].append(color)
                        if palette_type == '__global__':
                            save_palettes(color_palettes)
                        else:
                            save_project_palettes(self.view.window(), color_palettes)
                        self.show_color_info(update=True)
                        break

    def delete_palette(self, palette_type, palette_name):
        """ Delete palette """
        if palette_type == "__special__":
            if palette_name == 'Favorites':
                save_palettes([], favs=True)
                self.show_palettes(delete=True, update=True)
        elif palette_type in ('__global__', '__project__'):
            if palette_type == '__global__':
                color_palettes = get_palettes()
            else:
                color_palettes = get_project_palettes(self.view.window())
            count = -1
            index = None
            for palette in color_palettes:
                count += 1
                if palette_name == palette['name']:
                    index = count
                    break
            if index is not None:
                del color_palettes[index]
                if palette_type == '__global__':
                    save_palettes(color_palettes)
                else:
                    save_project_palettes(self.view.window(), color_palettes)
                self.show_palettes(delete=True, update=True)

    def delete_color(self, color, palette_type, palette_name):
        """ Delete color """
        if palette_type == '__special__':
            if palette_name == "Favorites":
                favs = get_favs()['colors']
                if color in favs:
                    favs.remove(color)
                    save_palettes(favs, favs=True)
                    self.show_colors(palette_type, palette_name, delete=True, update=True)
        elif palette_type in ('__global__', '__project__'):
            if palette_type == '__global__':
                color_palettes = get_palettes()
            else:
                color_palettes = get_project_palettes(self.view.window())
            for palette in color_palettes:
                if palette_name == palette['name']:
                    if color in palette['colors']:
                        palette['colors'].remove(color)
                        if palette_type == '__global__':
                            save_palettes(color_palettes)
                        else:
                            save_project_palettes(self.view.window(), color_palettes)
                        self.show_colors(palette_type, palette_name, delete=True, update=True)
                        break

    def add_fav(self, color):
        """ Add favorite """
        favs = get_favs()['colors']
        favs.append(color)
        save_palettes(favs, favs=True)
        self.show_color_info(update=True)

    def remove_fav(self, color):
        """ Remove favorite """
        favs = get_favs()['colors']
        favs.remove(color)
        save_palettes(favs, favs=True)
        self.show_color_info(update=True)

    def color_picker(self, color):
        """ Get color with color picker """
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

    def insert_color(self, target_color, convert=None):
        """ Insert colors """
        sels = self.view.sel()
        if (len(sels) == 1 and sels[0].size() == 0):
            point = sels[0].begin()
            insert_calc = InsertionCalc(self.view, point, target_color, convert)
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

    def format_palettes(self, color_list, label, palette_type, caption=None, color=None, delete=False):
        """ Format color palette previews """
        colors = ['<h1 class="header">%s</h1>' % label]
        if caption:
            colors.append('<span class="caption">%s</span><br>' % caption)
        if delete:
            label = '__delete__palette__:%s:%s' % (palette_type, label)
        elif color:
            label = '__add_palette_color__:%s:%s:%s' % (color, palette_type, label)
        else:
            label = '__colors__:%s:%s' % (palette_type, label)
        colors.append(
            '<a href="%s">%s</a>' % (
                label,
                palette_preview(color_list, ch_theme.border_color)
            )
        )
        return ''.join(colors)

    def format_colors(self, color_list, label, palette_type, delete=None):
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
            if delete:
                colors.append(
                    '<a href="__delete_color__:%s:%s:%s">%s</a>' % (
                        f, palette_type, label, color_box(f, ch_theme.border_color, size=32)
                    )
                )
            else:
                colors.append(
                    '<a href="%s">%s</a>' % (
                        f, color_box(f, ch_theme.border_color, size=32)
                    )
                )
            count += 1
        return ''.join(colors)

    def format_info(self, color, alpha=None):
        """ Format the selected color info """
        rgba = RGBA(color)

        try:
            web_color = webcolors.hex_to_name(color)
        except:
            web_color = None

        color_picker = color_picker_available()
        s = sublime.load_settings('color_helper.sublime-settings')
        show_global_palettes = s.get('enable_global_user_palettes', True)
        show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        show_current_palette = s.get('enable_current_file_palette', True)
        show_current_project_palette = s.get('enable_project_palette', True)
        show_conversions = s.get('enable_color_conversions', True)
        show_picker = s.get('enable_color_picker', True)
        palettes_enabled = (
            show_global_palettes or show_project_palettes or
            show_favorite_palette or show_current_palette or
            show_current_project_palette
        )
        click_color_box_to_pick = s.get('click_color_box_to_pick', 'none')

        if click_color_box_to_pick == 'color_picker' and color_picker and show_picker:
            color_box_wrapper = ('<a href="__color_picker__:%s">' % color) + '%s</a> '
        elif click_color_box_to_pick == 'palette_picker' and palettes_enabled:
            color_box_wrapper = '<a href="__palettes__">%s</a> '
        else:
            color_box_wrapper = '%s '

        info = ['<h1 class="header">%s</h1>' % color]

        info.append(
            color_box_wrapper % color_box(color, ch_theme.border_color, size=64)
        )

        if click_color_box_to_pick != 'palette_picker' and palettes_enabled:
            info.append(
                '<a href="__palettes__">' +
                '<img style="width: 20px; height: 20px;" src="%s">' % ch_theme.color_palette +
                '</a>'
            )

        if click_color_box_to_pick != 'color_picker' and color_picker and show_picker:
            info.append(
                '<a href="__color_picker__:%s"><img style="width: 16px; height: 16px;" src="%s"></a>' % (color, ch_theme.dropper)
            )

        if show_global_palettes or show_project_palettes:
            info.append(
                '<a href="__add_color__:%s">' % color.lower() +
                '<img style="width: 20px; height: 20px;" src="%s">' % ch_theme.add +
                '</a>'
            )

        if show_favorite_palette:
            if color in get_favs()['colors']:
                info.append(
                    '<a href="__remove_fav__:%s">' % color.lower() +
                    '<img style="width: 20px; height: 20px;" src="%s">' % ch_theme.bookmark_selected +
                    '</a>'
                )
            else:
                info.append(
                    '<a href="__add_fav__:%s">' % color.lower() +
                    '<img style="width: 20px; height: 20px;" src="%s">' % ch_theme.bookmark +
                    '</a>'
                )

        if show_conversions:
            info.append('<br><br><h1 class="header">Conversions</h1>')
            if web_color:
                info.append(
                    '<span class="key"><a href="__convert__:%s:name" class="convert-link">name</a>:</span> ' % color +
                    '<span class="color-value">%s</span><br>' % web_color
                )

            info.append(
                '<span class="key"><a href="__convert__:%s:hex" class="convert-link">hex</a>:</span> ' % color +
                '<span class="color-value">%s</span><br>' % (color.lower() if not alpha else color[:-2].lower())
            )

            info.append(
                '<span class="key"><a href="__convert__:%s:rgb" class="convert-link">rgb</a>:</span> ' % color +
                '<span class="color-key">rgb</span>(<span class="color-value">%d, %d, %d</span>)' % (rgba.r, rgba.g, rgba.b) +
                '<br>'
            )

            info.append(
                '<span class="key"><a href="__convert__:%s:rgba" class="convert-link">rgba</a>:</span> ' % color +
                '<span class="color-key">rgba</span>(<span class="color-value">%d, %d, %d, %s</span>)' % (rgba.r, rgba.g, rgba.b, alpha if alpha else '1') +
                '<br>'
            )

            h, l, s = rgba.tohls()

            info.append(
                '<span class="key"><a href="__convert__:%s:hsl" class="convert-link">hsl</a>:</span> ' % color +
                '<span class="color-key">hsl</span>(<span class="color-value">%s, %s%%, %s%%</span>)' % (
                    fmt_float(h * 360.0),
                    fmt_float(s * 100.0),
                    fmt_float(l * 100.0)
                ) +
                '<br>'
            )

            info.append(
                '<span class="key"><a href="__convert__:%s:hsla" class="convert-link">hsla</a>:</span> ' % color +
                '<span class="color-key">hsla</span>(<span class="color-value">%s, %s%%, %s%%, %s</span>)' % (
                    fmt_float(h * 360.0),
                    fmt_float(s * 100.0),
                    fmt_float(l * 100.0),
                    alpha if alpha else '1'
                ) +
                '<br>'
            )

        return ''.join(info)

    def show_palettes(self, delete=False, color=None, update=False):
        """ Show preview of all palettes """
        show_div = False
        s = sublime.load_settings('color_helper.sublime-settings')
        show_global_palettes = s.get('enable_global_user_palettes', True)
        show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        show_current_palette = s.get('enable_current_file_palette', True)
        show_current_project_palette = s.get('enable_project_palette', True)

        html = [
            '<style>%s</style>' % (ch_theme.css if ch_theme.css is not None else '') +
            '<div class="content">'
        ]

        if (not self.no_info and not delete) or color:
            html.append(
                '<a href="__info__"><img style="width: 20px; height: 20px;" src="%s"></a>' % ch_theme.back_arrow
            )
        elif delete:
            html.append('<a href="__palettes__"><img style="width: 20px; height: 20px;" src="%s"></a>' % ch_theme.back_arrow)

        if not delete and not color and (show_global_palettes or show_project_palettes or show_favorite_palette):
            html.append(
                '<a href="__delete__palettes__"><img style="width: 20px; height: 20px;" src="%s"></a>' % ch_theme.trash
            )

        if delete:
            html.append('<div class="delete">Click to delete palette.</div>')
        elif color:
            html.append('<div class="add">Click to add %s to palette.</div>' % color)

        if color:
            html.append(
                '<h1 class="header">New Palette</h1>' +
                '<a href="__create_palette__:__global__:%s" class="control-link">Create New Palette</a><br><br>' % color +
                '<a href="__create_palette__:__project__:%s" class="control-link">Create New Project Palette</a>' % color +
                '<div class="divider"></div>'
            )

        if show_favorite_palette:
            favs = get_favs()
            if len(favs['colors']) or color:
                show_div = True
                html.append(self.format_palettes(favs['colors'], favs['name'], '__special__', delete=delete, color=color))

        if show_current_palette:
            current_colors = self.view.settings().get('color_helper_file_palette', [])
            if not delete and not color and len(current_colors):
                show_div = True
                html.append(self.format_palettes(current_colors, "Current Colors", '__special__', delete=delete, color=color))

        if show_current_project_palette:
            data = self.view.window().project_data()
            project_colors = [] if data is None else data.get('color_helper_project_palette', [])
            if not delete and not color and len(project_colors):
                show_div = True
                html.append(self.format_palettes(project_colors, "Project Colors", '__special__', delete=delete, color=color))

        if show_div:
            html.append('<div class="divider"></div>')
            show_div = False

        if show_global_palettes:
            for palette in get_palettes():
                show_div = True
                name = palette.get("name")
                html.append(self.format_palettes(palette.get('colors', []), name, '__global__', palette.get('caption'), delete=delete, color=color))

        if show_project_palettes:
            for palette in get_project_palettes(self.view.window()):
                if show_div:
                    show_div = False
                    html.append('<div class="divider"></div>')
                name = palette.get("name")
                html.append(self.format_palettes(palette.get('colors', []), name, '__project__', palette.get('caption'), delete=delete, color=color))

        html.append('</div>')

        if update:
            self.view.update_popup(''.join(html))
        else:
            self.view.show_popup(
                ''.join(html), location=-1, max_width=600,
                on_navigate=self.on_navigate,
                flags=sublime.COOPERATE_WITH_AUTO_COMPLETE
            )

    def show_colors(self, palette_type, palette_name, delete=False, update=False):
        """ Show colors under the given palette """
        target = None
        current = False
        if palette_type == "__special__":
            if palette_name == "Current Colors":
                current = True
                target = {
                    "name": palette_name,
                    "colors": self.view.settings().get('color_helper_file_palette', [])
                }
            elif palette_name == "Project Colors":
                data = self.view.window().project_data()
                current = True
                target = {
                    "name": palette_name,
                    "colors": [] if data is None else data.get('color_helper_project_palette', [])
                }
            elif palette_name == "Favorites":
                target = get_favs()
        elif palette_type == "__global__":
            for palette in get_palettes():
                if palette_name == palette['name']:
                    target = palette
        elif palette_type == "__project__":
            for palette in get_project_palettes(self.view_window()):
                if palette_name == palette['name']:
                    target = palette

        if target is not None:
            html = [
                '<style>%s</style>' % (ch_theme.css if ch_theme.css is not None else '') +
                '<div class="content">'
            ]

            if not delete:
                html.append(
                    '<a href="__palettes__"><img style="width: 20px; height: 20px;" src="%s"></a>' % ch_theme.back_arrow
                )
                if not current:
                    html.append(
                        '<a href="__delete_colors__:%s:%s"><img style="width: 20px; height: 20px;" src="%s"></a>' % (
                            palette_type, target['name'], ch_theme.trash
                        )
                    )
            else:
                html.append(
                    '<a href="__colors__:%s:%s"><img style="width: 20px; height: 20px;" src="%s"></a>' % (
                        palette_type, target['name'], ch_theme.back_arrow
                    )
                )

            if delete:
                html.append('<div class="delete">Click to delete color.</div>')

            html.append(
                self.format_colors(target['colors'], target['name'], palette_type, delete) +
                '</div>'
            )

            if update:
                self.view.update_popup(''.join(html))
            else:
                self.view.show_popup(
                    ''.join(html), location=-1, max_width=600,
                    on_navigate=self.on_navigate,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE
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
            alpha = None
            if start < visible.begin():
                start = visible.begin()
            if end > visible.end():
                end = visible.end()
            bfr = self.view.substr(sublime.Region(start, end))
            ref = point - start
            for m in COLOR_RE.finditer(bfr):
                print(m.group(0))
                if ref >= m.start(0) and ref < m.end(0):
                    color, alpha = translate_color(m)
                    print(color)
                    break
        if color is not None:
            if alpha is not None:
                color += "%02X" % int('%.0f' % (float(alpha) * 255.0))

            html = [
                '<style>%s</style>' % (ch_theme.css if ch_theme.css is not None else '') +
                '<div class="content">'
            ]

            html.append(
                self.format_info(color.lower(), alpha) +
                '</div>'
            )

            if update:
                self.view.update_popup(''.join(html))
            else:
                self.view.show_popup(
                    ''.join(html), location=-1, max_width=600,
                    on_navigate=self.on_navigate,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE
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

    def is_enabled(self, mode="palette", palette_name=None, color=None):
        s = sublime.load_settings('color_helper.sublime-settings')
        return (
            mode == "info" or
            s.get('enable_global_user_palettes', True) or
            s.get('enable_project_user_palettes', True) or
            s.get('enable_favorite_palette', True) or
            s.get('enable_current_file_palette', True) or
            s.get('enable_project_palette', True)
        )


class ColorHelperFileIndexCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if get_scope(self.view, skip_sel_check=True):
            if ch_file_thread is None or not ch_file_thread.is_alive():
                start_file_index(self.view)
            else:
                sublime.error_message("File indexer is already running!")
        else:
            sublime.error_message('Cannot index colors in this file!')

    def is_enabled(self):
        s = sublime.load_settings('color_helper.sublime-settings')
        return s.get('enable_current_file_palette', True)


class ColorHelperProjectIndexCommand(sublime_plugin.WindowCommand):
    def run(self, clear_cache=False):
        global ch_project_thread
        if ch_project_thread is None or not ch_project_thread.is_alive():
            ch_project_thread = ChProjectIndexThread(self.window, get_project_folders(self.window), clear_cache=clear_cache)
            ch_project_thread.start()
            sublime.status_message('Project color index started...')
        else:
            sublime.error_message('Project indexer is already running!')

    def is_enabled(self, **kwargs):
        s = sublime.load_settings('color_helper.sublime-settings')
        return s.get('enable_project_palette', True)


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
        global ch_project_thread
        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        show_current_project_palette = s.get('enable_project_palette', True)
        if show_current_palette and view.settings().get('color_helper_file_palette', None) is None:
            view.settings().set('color_helper_file_palette', [])
            start_file_index(view)
        if show_current_project_palette:
            window = view.window()
            data = window.project_data()
            if window and (None if data is None else data.get('color_helper_project_palette', None)) is None:
                if (ch_project_thread is None or not ch_project_thread.is_alive()):
                    ch_project_thread = ChProjectIndexThread(window, get_project_folders(window))
                    ch_project_thread.start()
                    sublime.status_message("Project color index started...")

    def on_post_save(self, view):
        global ch_project_thread
        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        show_current_project_palette = s.get('enable_project_palette', True)
        if show_current_palette:
            start_file_index(view)
        if show_current_project_palette:
            window = view.window()
            if (ch_project_thread is None or not ch_project_thread.is_alive()) and window:
                ch_project_thread = ChProjectIndexThread(window, get_project_folders(window))
                ch_project_thread.start()
                sublime.status_message("Project color index started...")

    def on_clone(self, view):
        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        if show_current_palette:
            start_file_index(view)


class ChProjectIndexThread(threading.Thread):
    def __init__(self, window, project_folders, clear_cache=False):
        s = sublime.load_settings('color_helper.sublime-settings')
        scan_settings = s.get('project_file_scan_extensions', {})
        self.ignore = ['.', '..'] + scan_settings.get("ignore_folders", [".svn", ".git"])
        self.html_ext = scan_settings.get("html", [".html", ".html"])
        self.css_ext = scan_settings.get('css', [".css"])
        self.sass_ext = scan_settings.get('sass', [".sass", ".scss"])
        self.ase_ext = scan_settings.get('ase', ['.ase'])
        self.all_ext = self.html_ext + self.css_ext + self.sass_ext + self.ase_ext
        self.project_folders = project_folders
        self.hex = re.compile(br'\#(?:[\dA-Fa-f]{3}){1,2}\b')
        self.colors = []
        self.abort = False
        self.window = window
        self.win_id = window.id()
        self.cache = os.path.join(get_cache_dir(), "%d.cache" % self.window.id())
        self.clear_cache = clear_cache
        threading.Thread.__init__(self)

    def kill(self):
        """ Kill thread """
        self.abort = True
        while self.is_alive():
            pass

    def save_project_data(self, colors):
        """ Store project colors in project data """
        colors.sort()
        data = self.window.project_data()
        if data is None:
            data = {'folders': [{'path': f} for f in self.window.folders()]}
        debug('Project Colors = ', colors)
        data['color_helper_project_palette'] = colors
        self.window.set_project_data(data)
        sublime.status_message('Project color index complete...')

    def save_results(self, cache_file, cache):
        """ Save cache results """
        try:
            with codecs.open(cache_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(cache))
        except:
            pass

    def crawl_files(self, root, files, colors, old_cache, cache):
        """ Crawl project files and index colors from various sources """
        for file_name in files:
            if self.abort:
                break
            file_path = os.path.join(root, file_name)
            ext = os.path.splitext(file_path)[1].lower()
            if ext in self.all_ext:
                mtime = os.path.getmtime(file_path)
                if mtime != old_cache.get(file_path, {}).get('time', 0):
                    local_colors = set()
                    try:
                        with codecs.open(file_path, 'rb') as f:
                            search_text = False
                            if ext in self.css_ext:
                                content = self.parse_css(f.read())
                                search_text = True
                            elif ext in self.sass_ext:
                                content = self.parse_css(f.read(), single_line_comments=True)
                                search_text = True
                            elif ext in self.html_ext:
                                content = self.parse_html(f.read())
                                search_text = True
                            elif ext in self.ase_ext:
                                content = ase_load(f.read())
                                for palette in content:
                                    for color in palette.get('colors', []):
                                        c = color['color']
                                        colors.add(c)
                                        local_colors.add(c)
                            if search_text:
                                for m in INDEX_ALL_RE.finditer(content):
                                    c, a = translate_color(m)
                                    colors.add(c)
                                    local_colors.add(c)
                            cache[file_path] = {'time': mtime, 'colors': list(local_colors)}
                    except:
                        # cache[file_path] = {'time': 0, 'colors': []}
                        cache[file_path] = {'time': 0, 'colors': [], 'error': str(traceback.format_exc())}
                else:
                    colors |= set(old_cache[file_path].get('colors', []))
                    cache[file_path] = old_cache[file_path]

    def parse_css(self, content, single_line_comments=False):
        # Strip out comment and strings so that we can scan for colors
        # without worrying about irrelevant text being processed.
        index = 0
        slash, star, bslash, squote, dquote, space, newline = b'/*\\\'" \n'
        text = [space]

        while index < len(content):
            c = content[index]
            if c == slash and content[index + 1] == star:
                # multi line comment
                index += 2
                while index < len(content):
                    c = content[index]
                    if c == star and content[index + 1] == slash:
                        index += 2
                        break
                    index += 1
            elif single_line_comments and c == slash and content[index + 1] == slash:
                # single line comment
                index += 2
                while index < len(content):
                    c = content[index]
                    if c == newline:
                        text.append(c)
                        index += 1
                        break
                    index += 1
            elif c in (squote, dquote):
                # strings
                start = c
                index += 1
                while index < len(content):
                    c = content[index]
                    if c == bslash:
                        index += 2
                    elif c == start:
                        index += 1
                        break
                    else:
                        index += 1
            else:
                text.append(c)
                index += 1

        return bytes(text)

    def parse_html(self, content):
        """ Strip comments and parse css from tag style attributes and style tags """
        bstrs = []

        for m in TAG_HTML_RE.finditer(content):
            if m.group('style'):
                bstrs.append(self.parse_css(m.group('css')))
            else:
                for attr in TAG_STYLE_ATTR_RE.finditer(m.group('attr')):
                    # Parse HTML style attributes as css
                    for attr in TAG_STYLE_ATTR_RE.finditer(m.group('attr')):
                        bstrs.append(self.parse_css(b'{' + attr.group('content')[1:-1] + b'}'))

        return b''.join(bstrs)

    def run(self):
        """ Walk the project structure and index colors in CSS, HTML, and ASE files """
        colors = set()
        if len(self.project_folders):
            to_crawl = [pf['path'] for pf in self.project_folders]
            sub_crawl = []
            cache = {}
            old_cache = {}
            folder = None
            main_folder = None

            if not self.clear_cache and os.path.exists(self.cache):
                try:
                    with codecs.open(self.cache, 'r', encoding='utf-8') as f:
                        old_cache = json.loads(f.read())
                except:
                    pass

            while (len(to_crawl) or len(sub_crawl)):
                if self.abort:
                    break
                if len(sub_crawl):
                    folder = sub_crawl.pop(0)
                elif len(to_crawl):
                    folder = to_crawl.pop(0)
                    main_folder = folder
                for root, dirs, files in os.walk(folder):
                    if self.abort:
                        break
                    sub_crawl += [os.path.join(root, d) for d in dirs if d not in self.ignore]
                    self.crawl_files(root, files, colors, old_cache, cache)

            if main_folder is not None and not self.abort:
                self.save_results(self.cache, cache)
                sublime.set_timeout(lambda c=list(colors): self.save_project_data(c))


class ChFileIndexThread(threading.Thread):
    """ Load up defaults """

    def __init__(self, view, source):
        """ Setup the thread """
        self.abort = False
        self.view = view
        self.webcolor_names = re.compile(
            r'\b(%s)\b' % '|'.join(
                [name for name in webcolors.css3_names_to_hex.keys()]
            )
        )
        self.source = source
        threading.Thread.__init__(self)

    def update_index(self, view, colors):
        """ Code to run """
        try:
            colors.sort()
            sublime.status_message('File color index complete...')
            view.settings().set('color_helper_file_palette', colors)
            debug('Colors:\n', colors)
        except Exception as e:
            debug(e)
            pass

    def kill(self):
        """ Kill thread """
        self.abort = True
        while self.is_alive():
            pass

    def run(self):
        """ Thread loop """
        if self.source:
            self.index_colors()

    def index_colors(self):
        """ Index colors in file """
        colors = set()
        for m in COLOR_RE.finditer(self.source):
            if self.abort:
                break
            color, alpha = translate_color(m)
            if color is not None:
                colors.add(color)
        for m in self.webcolor_names.finditer(self.source):
            if self.abort:
                break
            colors.add(webcolors.name_to_hex(m.group(0)))
        if not self.abort:
            sublime.set_timeout(
                lambda view=self.view, colors=list(colors): self.update_index(view, colors), 0
            )


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
        self.save_palettes = False

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
                scope and
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
                            m.group('hsl') or m.group('hsla') or m.group('webcolors')
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


###########################
# Tooltip Theme
###########################
class ChTheme(object):
    def __init__(self):
        self.setup()

    def has_changed(self):
        # Reload events recently are always reloading,
        # So maybe we will use this to check if reload is needed.
        pref_settings = sublime.load_settings('Preferences.sublime-settings')
        return self.scheme_file != pref_settings.get('color_scheme')

    def get_theme_res(self, *args, link=False):
        res = '/'.join(('Packages', self.tt_theme) + args)
        return 'res://' + res if link else res

    def setup(self):
        pref_settings = sublime.load_settings('Preferences.sublime-settings')

        self.scheme_file = pref_settings.get('color_scheme')
        try:
            self.lums = scheme_lums(self.scheme_file)
        except:
            self.lums = 128

        self.tt_theme = ch_settings.get('tooltip_theme', 'ColorHelper/tt_theme')

        if self.lums <= 127:
            self.border_color = '#CCCCCC'
            self.css_file = self.get_theme_res('css', 'dark.css')
            self.cross = self.get_theme_res('images', 'cross_dark.png', link=True)
            self.back_arrow = self.get_theme_res('images', 'back_dark.png', link=True)
            self.bookmark = self.get_theme_res('images', 'bookmark_dark.png', link=True)
            self.bookmark_selected = self.get_theme_res('images', 'bookmark_selected_dark.png', link=True)
            self.dropper = self.get_theme_res('images', 'dropper_dark.png', link=True)
            self.color_palette = self.get_theme_res('images', 'palette_dark.png', link=True)
            self.trash = self.get_theme_res('images', 'trash_dark.png', link=True)
            self.add = self.get_theme_res('images', 'plus_dark.png', link=True)
        else:
            self.border_color = '#333333'
            self.css_file = self.get_theme_res('css', 'light.css')
            self.cross = self.get_theme_res('images', 'cross_light.png', link=True)
            self.back_arrow = self.get_theme_res('images', 'back_light.png', link=True)
            self.bookmark = self.get_theme_res('images', 'bookmark_light.png', link=True)
            self.bookmark_selected = self.get_theme_res('images', 'bookmark_selected_light.png', link=True)
            self.dropper = self.get_theme_res('images', 'dropper_light.png', link=True)
            self.color_palette = self.get_theme_res('images', 'palette_light.png', link=True)
            self.trash = self.get_theme_res('images', 'trash_light.png', link=True)
            self.add = self.get_theme_res('images', 'plus_light.png', link=True)

        try:
            self.css = sublime.load_resource(self.css_file).replace('\r', '')
        except:
            self.css = None


###########################
# Plugin Initialization
###########################
def init_plugin():
    """ Setup plugin variables and objects """
    global ch_settings
    global ch_thread
    global ch_theme
    global ch_file_thread

    # Make sure cache folder exists
    cache_folder = get_cache_dir()
    if not os.path.exists(cache_folder):
        os.makedirs(cache_folder)

    # Clean up cache
    win_ids = [win.id() for win in sublime.windows()]
    for f in os.listdir(cache_folder):
        if f.lower().endswith('.cache'):
            try:
                win_id = int(os.path.splitext(f)[0])
                if win_id not in win_ids:
                    os.remove(os.path.join(cache_folder, f))
            except:
                pass

    # Setup settings
    ch_settings = sublime.load_settings('color_helper.sublime-settings')

    # Theme setup
    ch_theme = ChTheme()

    # Setup reload events
    pref_settings = sublime.load_settings('Preferences.sublime-settings')
    pref_settings.clear_on_change('colorhelper_reload')
    pref_settings.add_on_change('colorhelper_reload', ch_theme.setup)
    ch_settings.clear_on_change('reload')
    ch_settings.add_on_change('reload', ch_theme.setup)

    # Start event thread
    if ch_thread is not None:
        ch_thread.kill()
    ch_thread = ChThread()
    ch_thread.start()


def plugin_loaded():
    """ Setup plugin """
    init_plugin()


def plugin_unloaded():
    ch_thread.kill()
    if ch_file_thread is not None:
        ch_file_thread.kill()
    if ch_project_thread is not None:
        ch_project_thread.kill()
