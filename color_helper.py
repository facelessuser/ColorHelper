"""
ColorHelper.

Copyright (c) 2015 - 2016 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
from ColorHelper.lib.rgba import RGBA
from ColorHelper.lib import csscolors
import threading
from time import time, sleep
import re
import os
import mdpopups
import ColorHelper.color_helper_util as util
from ColorHelper.color_helper_insert import InsertCalc, PickerInsertCalc
from ColorHelper.multiconf import get as qualify_settings
import traceback

__pc_name__ = "ColorHelper"

LATEST_SUPPORTED_MDPOPUPS = mdpopups.version() >= (1, 10, 0)

DISTORTION_FIX = int(sublime.version()) < 3118
PHANTOM_SUPPORT = (mdpopups.version() >= (1, 7, 3)) and (int(sublime.version()) >= 3118)

PREVIEW_SCALE_Y = 2
PALETTE_SCALE_X = 8
PALETTE_SCALE_Y = 2
BORDER_SIZE = 2
PREVIEW_BORDER_SIZE = 1

reload_flag = False
ch_last_updated = None
ch_settings = None
unloading = False

if 'ch_thread' not in globals():
    ch_thread = None

if 'ch_file_thread' not in globals():
    ch_file_thread = None

if 'ch_preview_thread' not in globals():
    ch_preview_thread = None


###########################
# Helper Classes/Functions
###########################
def start_file_index(view):
    """Kick off current file color index."""
    global ch_file_thread
    if view is not None and (ch_file_thread is None or not ch_file_thread.is_alive()):
        rules = util.get_rules(view)
        if rules:
            scope = util.get_scope(view, rules, skip_sel_check=True)
            if scope:
                source = []
                for r in view.find_by_selector(scope):
                    source.append(view.substr(r))
                util.debug('Regions to search:\n', source)
                if len(source):
                    ch_file_thread = ChFileIndexThread(
                        view, ' '.join(source),
                        rules.get('allowed_colors', []),
                        rules.get('use_hex_argb', False)
                    )
                    ch_file_thread.start()
                    s = sublime.load_settings('color_helper.sublime-settings')
                    if s.get('show_index_status', True):
                        sublime.status_message('File color indexer started...')


def preview_is_on_left():
    """Return boolean for positioning preview on left/right."""
    return ch_settings.get('inline_preview_position') != 'right'


###########################
# Main Code
###########################
class ColorHelperCommand(sublime_plugin.TextCommand):
    """Color Helper command object."""

    def on_hide(self):
        """Hide popup event."""

        self.view.settings().set('color_helper.popup_active', False)
        self.view.settings().set('color_helper.popup_auto', self.auto)

    def on_navigate(self, href):
        """Handle link clicks."""

        if href.startswith('__insert__'):
            parts = href.split(':', 3)
            self.show_insert(parts[1], parts[2], parts[3])
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
        elif href.startswith('__convert_alpha__'):
            parts = href.split(':', 2)
            self.insert_color(parts[1], parts[2], alpha=True)
        elif href.startswith('__convert__'):
            parts = href.split(':', 2)
            self.insert_color(parts[1], parts[2])

    def repop(self):
        """Setup thread to repopup tooltip."""

        return
        if ch_thread.ignore_all:
            return
        now = time()
        ch_thread.modified = True
        ch_thread.time = now

    def prompt_palette_name(self, palette_type, color):
        """Prompt user for new palette name."""

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
        """Add color to new color palette."""

        if palette_type == '__global__':
            color_palettes = util.get_palettes()
            for palette in color_palettes:
                if palette_name == palette['name']:
                    sublime.error_message('The name of "%s" is already in use!')
                    return
            color_palettes.append({"name": palette_name, 'colors': [color]})
            util.save_palettes(color_palettes)
        elif palette_type == '__project__':
            color_palettes = util.get_project_palettes(self.view.window())
            for palette in color_palettes:
                if palette_name == palette['name']:
                    sublime.error_message('The name of "%s" is already in use!')
                    return
            color_palettes.append({"name": palette_name, 'colors': [color]})
            util.save_project_palettes(self.view.window(), color_palettes)
        self.repop()

    def add_palette(self, color, palette_type, palette_name):
        """Add pallete."""

        if palette_type == "__special__":
            if palette_name == 'Favorites':
                favs = util.get_favs()['colors']
                if color not in favs:
                    favs.append(color)
                util.save_palettes(favs, favs=True)
                self.show_color_info(update=True)
        elif palette_type in ('__global__', '__project__'):
            if palette_type == '__global__':
                color_palettes = util.get_palettes()
            else:
                color_palettes = util.get_project_palettes(self.view.window())
            for palette in color_palettes:
                if palette_name == palette['name']:
                    if color not in palette['colors']:
                        palette['colors'].append(color)
                        if palette_type == '__global__':
                            util.save_palettes(color_palettes)
                        else:
                            util.save_project_palettes(self.view.window(), color_palettes)
                        self.show_color_info(update=True)
                        break

    def delete_palette(self, palette_type, palette_name):
        """Delete palette."""

        if palette_type == "__special__":
            if palette_name == 'Favorites':
                util.save_palettes([], favs=True)
                self.show_palettes(delete=True, update=False)
        elif palette_type in ('__global__', '__project__'):
            if palette_type == '__global__':
                color_palettes = util.get_palettes()
            else:
                color_palettes = util.get_project_palettes(self.view.window())
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
                    util.save_palettes(color_palettes)
                else:
                    util.save_project_palettes(self.view.window(), color_palettes)
                self.show_palettes(delete=True, update=False)

    def delete_color(self, color, palette_type, palette_name):
        """Delete color."""

        if palette_type == '__special__':
            if palette_name == "Favorites":
                favs = util.get_favs()['colors']
                if color in favs:
                    favs.remove(color)
                    util.save_palettes(favs, favs=True)
                    self.show_colors(palette_type, palette_name, delete=True, update=False)
        elif palette_type in ('__global__', '__project__'):
            if palette_type == '__global__':
                color_palettes = util.get_palettes()
            else:
                color_palettes = util.get_project_palettes(self.view.window())
            for palette in color_palettes:
                if palette_name == palette['name']:
                    if color in palette['colors']:
                        palette['colors'].remove(color)
                        if palette_type == '__global__':
                            util.save_palettes(color_palettes)
                        else:
                            util.save_project_palettes(self.view.window(), color_palettes)
                        self.show_colors(palette_type, palette_name, delete=True, update=False)
                        break

    def add_fav(self, color):
        """Add favorite."""

        favs = util.get_favs()['colors']
        favs.append(color)
        util.save_palettes(favs, favs=True)
        # For some reason if using update,
        # the convert divider will be too wide.
        self.show_color_info(update=False)

    def remove_fav(self, color):
        """Remove favorite."""

        favs = util.get_favs()['colors']
        favs.remove(color)
        util.save_palettes(favs, favs=True)
        # For some reason if using update,
        # the convert divider will be too wide.
        self.show_color_info(update=False)

    def color_picker(self, color):
        """Get color with color picker."""

        if self.color_picker_package:
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
        else:
            if not self.no_info:
                on_cancel = {'command': 'color_helper', 'args': {'mode': "info", "auto": self.auto}}
            elif not self.no_palette:
                on_cancel = {'command': 'color_helper', 'args': {'mode': "palette", "auto": self.auto}}
            else:
                on_cancel = None
            rules = util.get_rules(self.view)
            allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
            use_hex_argb = rules.get("use_hex_argb", False) if rules else False
            compress_hex = rules.get("compress_hex_output", False) if rules else False
            self.view.run_command(
                'color_helper_picker', {
                    'color': color,
                    'allowed_colors': allowed_colors,
                    'use_hex_argb': use_hex_argb,
                    'compress_hex': compress_hex,
                    'on_done': {'command': 'color_helper', 'args': {'mode': "color_picker_result"}},
                    'on_cancel': on_cancel
                }
            )

    def insert_color(self, target_color, convert=None, picker=False, alpha=False):
        """Insert colors."""

        sels = self.view.sel()
        if (len(sels) == 1 and sels[0].size() == 0):
            point = sels[0].begin()
            parts = target_color.split('@')
            target_color = parts[0]
            dlevel = len(parts[1]) if len(parts) > 1 else 3
            if not picker:
                rules = util.get_rules(self.view)
                use_hex_argb = rules.get("use_hex_argb", False) if rules else False
                allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
                compress_hex = rules.get('compress_hex_output', False) if rules else False
                calc = InsertCalc(self.view, point, target_color, convert, allowed_colors, use_hex_argb)
                calc.calc()
                if alpha:
                    calc.alpha_hex = target_color[-2:]
                    calc.alpha = util.fmt_float(float(int(calc.alpha_hex, 16)) / 255.0, dlevel)
                if calc.web_color and not calc.alpha:
                    value = calc.web_color
                elif calc.convert_rgb:
                    value = "%d, %d, %d" % (
                        int(calc.color[1:3], 16),
                        int(calc.color[3:5], 16),
                        int(calc.color[5:7], 16)
                    )
                    if calc.alpha:
                        value += ', %s' % calc.alpha
                    value = ("rgba(%s)" if calc.alpha else "rgb(%s)") % value
                elif calc.convert_gray:
                    value = "%d" % int(calc.color[1:3], 16)
                    if calc.alpha:
                        value += ', %s' % calc.alpha
                    value = "gray(%s)" % value
                elif calc.convert_hsl:
                    hsl = RGBA(calc.color)
                    h, l, s = hsl.tohls()
                    value = "%s, %s%%, %s%%" % (
                        util.fmt_float(h * 360.0),
                        util.fmt_float(s * 100.0),
                        util.fmt_float(l * 100.0)
                    )
                    if calc.alpha:
                        value += ', %s' % calc.alpha
                    value = ("hsla(%s)" if calc.alpha else "hsl(%s)") % value
                elif calc.convert_hwb:
                    hwb = RGBA(calc.color)
                    h, w, b = hwb.tohwb()
                    value = "%s, %s%%, %s%%" % (
                        util.fmt_float(h * 360.0),
                        util.fmt_float(w * 100.0),
                        util.fmt_float(b * 100.0)
                    )
                    if calc.alpha:
                        value += ', %s' % calc.alpha
                    value = "hwb(%s)" % value
                else:
                    use_upper = ch_settings.get("upper_case_hex", False)
                    color = calc.color
                    if calc.alpha_hex:
                        if convert == 'ahex':
                            color = '#' + calc.alpha_hex + calc.color[1:]
                        else:
                            color = calc.color + calc.alpha_hex
                    if compress_hex:
                        color = util.compress_hex(color)
                    value = color.upper() if use_upper else color.lower()
            else:
                rules = util.get_rules(self.view)
                allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
                calc = PickerInsertCalc(self.view, point, allowed_colors)
                calc.calc()
                value = target_color
            self.view.sel().subtract(sels[0])
            self.view.sel().add(calc.region)
            self.view.run_command("insert", {"characters": value})
        self.view.hide_popup()

    def format_palettes(self, color_list, label, palette_type, caption=None, color=None, delete=False):
        """Format color palette previews."""

        colors = ['\n## %s\n' % label]
        if caption:
            colors.append('%s\n' % caption)
        if delete:
            label = '__delete__palette__:%s:%s' % (palette_type, label)
        elif color:
            label = '__add_palette_color__:%s:%s:%s' % (color, palette_type, label)
        else:
            label = '__colors__:%s:%s' % (palette_type, label)

        colors.append(
            '[%s](%s)' % (
                mdpopups.color_box(
                    color_list, '#cccccc', '#333333',
                    height=self.color_h, width=self.palette_w * PALETTE_SCALE_X,
                    border_size=BORDER_SIZE, check_size=self.check_size(self.color_h)
                ),
                label
            )
        )
        return ''.join(colors)

    def format_colors(self, color_list, label, palette_type, delete=None):
        """Format colors under palette."""

        colors = ['\n## %s\n' % label]
        count = 0

        check_size = self.check_size(self.color_h)
        for f in color_list:
            parts = f.split('@')
            if len(parts) > 1:
                color = parts[0]
            else:
                color = f
            no_alpha_color = color[:-2] if len(f) > 7 else color
            if count != 0 and (count % 8 == 0):
                colors.append('\n\n')
            elif count != 0:
                if sublime.platform() == 'windows':
                    colors.append('&nbsp; ')
                else:
                    colors.append('&nbsp;')
            if delete:
                colors.append(
                    '[%s](__delete_color__:%s:%s:%s)' % (
                        mdpopups.color_box(
                            [no_alpha_color, color], '#cccccc', '#333333',
                            height=self.color_h, width=self.color_w, border_size=BORDER_SIZE,
                            check_size=check_size
                        ),
                        f, palette_type, label,
                    )
                )
            else:
                colors.append(
                    '[%s](__insert__:%s:%s:%s)' % (
                        mdpopups.color_box(
                            [no_alpha_color, color], '#cccccc', '#333333',
                            height=self.color_h, width=self.color_w, border_size=BORDER_SIZE,
                            check_size=check_size
                        ), f, palette_type, label
                    )
                )
            count += 1
        return ''.join(colors)

    def format_info(self, color, template_vars, alpha=None):
        """Format the selected color info."""
        rgba = RGBA(color)

        rules = util.get_rules(self.view)
        allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
        use_hex_argb = rules.get("use_hex_argb", False) if rules else None
        if alpha is not None:
            parts = alpha.split('.')
            dlevel = len(parts[1]) if len(parts) > 1 else None
            alpha_hex = alpha_hex_display = "%02x" % (util.round_int(float(alpha) * 255.0) & 0xFF)
            if dlevel is not None:
                alpha_hex += '@%d' % dlevel
        else:
            alpha_hex = ''

        try:
            web_color = csscolors.hex2name(rgba.get_rgb())
        except Exception:
            web_color = None

        h1, l, s = rgba.tohls()
        h2, w, b = rgba.tohwb()

        template_vars['color'] = color
        template_vars['color_dlevel'] = rgba.get_rgb().lower() + alpha_hex
        template_vars['web_color'] = web_color
        template_vars['hex_color'] = rgba.get_rgb().lower()
        template_vars['hex_alpha'] = 'ff' if not alpha else alpha_hex_display
        template_vars['ahex_color'] = rgba.get_rgb().lower()[1:]
        template_vars['alpha'] = alpha if alpha else '1'
        template_vars['rgb_r'] = str(rgba.r)
        template_vars['rgb_g'] = str(rgba.g)
        template_vars['rgb_b'] = str(rgba.b)
        template_vars['hsl_h'] = util.fmt_float(h1 * 360.0)
        template_vars['hsl_s'] = util.fmt_float(s * 100.0)
        template_vars['hsl_l'] = util.fmt_float(l * 100.0)
        template_vars['hwb_h'] = util.fmt_float(h2 * 360.0)
        template_vars['hwb_s'] = util.fmt_float(w * 100.0)
        template_vars['hwb_l'] = util.fmt_float(b * 100.0)

        s = sublime.load_settings('color_helper.sublime-settings')
        show_global_palettes = s.get('enable_global_user_palettes', True)
        show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        show_current_palette = s.get('enable_current_file_palette', True)
        show_conversions = s.get('enable_color_conversions', True)
        show_picker = s.get('enable_color_picker', True)
        palettes_enabled = (
            show_global_palettes or show_project_palettes or
            show_favorite_palette or show_current_palette
        )
        click_color_box_to_pick = s.get('click_color_box_to_pick', 'none')

        if click_color_box_to_pick == 'color_picker' and show_picker:
            template_vars['click_color_picker'] = True
        elif click_color_box_to_pick == 'palette_picker' and palettes_enabled:
            template_vars['click_palette_picker'] = True

        if click_color_box_to_pick != 'palette_picker' and palettes_enabled:
            template_vars['show_palette_menu'] = True
        if click_color_box_to_pick != 'color_picker' and show_picker:
            template_vars['show_picker_menu'] = True
        if show_global_palettes or show_project_palettes:
            template_vars['show_global_palette_menu'] = True
        if show_favorite_palette:
            template_vars['show_favorite_menu'] = True
            template_vars['is_marked'] = (rgba.get_rgb().lower() + alpha_hex) in util.get_favs()['colors']

        no_alpha_color = color[:-2] if len(color) > 7 else color
        template_vars['color_preview'] = (
            mdpopups.color_box(
                [no_alpha_color, color], '#cccccc', '#333333',
                height=self.color_h * PREVIEW_SCALE_Y, width=self.palette_w * PALETTE_SCALE_X,
                border_size=BORDER_SIZE, check_size=self.check_size(self.color_h)
            )
        )

        if show_conversions:
            template_vars['show_conversions'] = True
            template_vars['show_web_color'] = web_color and 'webcolors' in allowed_colors
            template_vars['show_hex_color'] = "hex" in allowed_colors
            if "hexa" in allowed_colors:
                template_vars['show_hexa_color'] = not use_hex_argb
                template_vars['show_ahex_color'] = bool(use_hex_argb)
            template_vars['show_rgb_color'] = "rgb" in allowed_colors
            template_vars['show_rgba_color'] = "rgba" in allowed_colors
            template_vars['show_gray_color'] = "gray" in allowed_colors and util.is_gray(rgba.get_rgb())
            template_vars['show_graya_color'] = "graya" in allowed_colors and util.is_gray(rgba.get_rgb())
            template_vars['show_hsl_color'] = "hsl" in allowed_colors
            template_vars['show_hsla_color'] = "hsla" in allowed_colors
            template_vars['show_hwb_color'] = "hwb" in allowed_colors
            template_vars['show_hwba_color'] = "hwba" in allowed_colors

    def show_insert(self, color, palette_type, palette_name, update=False):
        """Show insert panel."""

        sels = self.view.sel()
        if (len(sels) == 1 and sels[0].size() == 0):
            parts = color.split('@')
            dlevel = len(parts[1]) if len(parts) > 1 else 3
            point = sels[0].begin()
            rules = util.get_rules(self.view)
            use_hex_argb = rules.get("use_hex_argb", False) if rules else None
            allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
            calc = InsertCalc(self.view, point, parts[0], 'rgba', allowed_colors, bool(use_hex_argb))
            found = calc.calc()

            rules = util.get_rules(self.view)
            allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL

            secondary_alpha = found and calc.alpha is not None and calc.alpha != '1'

            rgba = RGBA(parts[0])
            alpha = util.fmt_float(float(rgba.a) / 255.0, dlevel)

            try:
                web_color = csscolors.hex2name(rgba.get_rgb())
            except Exception:
                web_color = None

            h1, l, s = rgba.tohls()
            h2, w, b = rgba.tohwb()

            template_vars = {
                "legacy": util.LEGACY_CLASS,
                "palette_type": palette_type,
                "palette_name": palette_name,
                "color": rgba.get_rgb(),
                "alpha_hex": rgba.get_rgba()[-2:],
                "color_alpha": rgba.get_rgba(),
                "color_ahex": rgba.get_rgba()[1:],
                "dlevel": ("@%d" % dlevel),
                "alpha": alpha,
                "current_alpha_hex": calc.alpha_hex if secondary_alpha else 'FF',
                "current_alpha": calc.alpha if secondary_alpha else '1',
                "rgb_r": rgba.r,
                "rgb_g": rgba.g,
                "rgb_b": rgba.b,
                "hsl_h": util.fmt_float(h1 * 360.0),
                "hsl_s": util.fmt_float(s * 100.0),
                "hsl_l": util.fmt_float(l * 100.0),
                "hwb_h": util.fmt_float(h2 * 360.0),
                "hwb_w": util.fmt_float(w * 100.0),
                "hwb_b": util.fmt_float(b * 100.0),
                "web_color": web_color,
                "secondary_alpha": secondary_alpha
            }

            template_vars['show_web_color'] = web_color and "webcolors" in allowed_colors
            template_vars['show_hex_color'] = "hex" in allowed_colors
            template_vars['show_hexa_color'] = "hexa" in allowed_colors and not bool(use_hex_argb)
            template_vars['show_ahex_color'] = "hexa" in allowed_colors and bool(use_hex_argb)
            template_vars['show_rgb_color'] = "rgb" in allowed_colors
            template_vars['show_rgba_color'] = "rgba" in allowed_colors
            template_vars['show_gray_color'] = "gray" in allowed_colors and util.is_gray(rgba.get_rgb())
            template_vars['show_graya_color'] = "graya" in allowed_colors and util.is_gray(rgba.get_rgb())
            template_vars['show_hsl_color'] = "hsl" in allowed_colors
            template_vars['show_hsla_color'] = "hsla" in allowed_colors
            template_vars['show_hwb_color'] = "hwb" in allowed_colors
            template_vars['show_hwba_color'] = "hwba" in allowed_colors

            if update:
                mdpopups.update_popup(
                    self.view,
                    sublime.load_resource('Packages/ColorHelper/panels/insert.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    template_vars=template_vars,
                    nl2br=False
                )
            else:
                self.view.settings().set('color_helper.popup_active', True)
                self.view.settings().set('color_helper.popup_auto', self.auto)
                mdpopups.show_popup(
                    self.view,
                    sublime.load_resource('Packages/ColorHelper/panels/insert.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars,
                    nl2br=False
                )

    def show_palettes(self, delete=False, color=None, update=False):
        """Show preview of all palettes."""

        show_div = False
        s = sublime.load_settings('color_helper.sublime-settings')
        show_global_palettes = s.get('enable_global_user_palettes', True)
        show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        show_current_palette = s.get('enable_current_file_palette', True)
        s = sublime.load_settings('color_helper.sublime-settings')
        show_picker = s.get('enable_color_picker', True) and self.no_info
        palettes = util.get_palettes()
        project_palettes = util.get_project_palettes(self.view.window())

        template_vars = {
            "legacy": util.LEGACY_CLASS,
            "color": (color if color else '#ffffffff'),
            "show_picker_menu": show_picker,
            "show_delete_menu": (
                not delete and not color and (show_global_palettes or show_project_palettes or show_favorite_palette)
            ),
            "back_target": "__info__" if (not self.no_info and not delete) or color else "__palettes__",
            "show_delete_ui": delete,
            "show_new_ui": bool(color),
            "show_favorite_palette": show_favorite_palette,
            "show_current_palette": show_current_palette,
            "show_global_palettes": show_global_palettes and len(palettes),
            "show_project_palettes": show_project_palettes and len(project_palettes)
        }

        if show_favorite_palette:
            favs = util.get_favs()
            if len(favs['colors']) or color:
                show_div = True
                template_vars['favorite_palette'] = (
                    self.format_palettes(favs['colors'], favs['name'], '__special__', delete=delete, color=color)
                )

        if show_current_palette:
            current_colors = self.view.settings().get('color_helper.file_palette', [])
            if not delete and not color and len(current_colors):
                show_div = True
                template_vars['current_palette'] = (
                    self.format_palettes(current_colors, "Current Colors", '__special__', delete=delete, color=color)
                )

        if show_global_palettes and len(palettes):
            if show_div:
                template_vars['show_separator'] = True
                show_div = False
            global_palettes = []
            for palette in palettes:
                show_div = True
                name = palette.get("name")
                global_palettes.append(
                    self.format_palettes(
                        palette.get('colors', []), name, '__global__', palette.get('caption'),
                        delete=delete,
                        color=color
                    )
                )
            template_vars['global_palettes'] = global_palettes

        if show_project_palettes and len(project_palettes):
            if show_div:
                show_div = False
                template_vars['show_project_separator'] = True
            project_palettes = []
            for palette in project_palettes:
                name = palette.get("name")
                project_palettes.append(
                    self.format_palettes(
                        palette.get('colors', []), name, '__project__', palette.get('caption'),
                        delete=delete,
                        color=color
                    )
                )
                template_vars['project_palettes'] = project_palettes

        if update:
            mdpopups.update_popup(
                self.view,
                sublime.load_resource('Packages/ColorHelper/panels/palettes.html'),
                wrapper_class="color-helper content",
                css=util.ADD_CSS,
                template_vars=template_vars,
                nl2br=False
            )
        else:
            self.view.settings().set('color_helper.popup_active', True)
            self.view.settings().set('color_helper.popup_auto', self.auto)
            mdpopups.show_popup(
                self.view,
                sublime.load_resource('Packages/ColorHelper/panels/palettes.html'),
                wrapper_class="color-helper content",
                css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                on_navigate=self.on_navigate,
                on_hide=self.on_hide,
                flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                template_vars=template_vars,
                nl2br=False
            )

    def show_colors(self, palette_type, palette_name, delete=False, update=False):
        """Show colors under the given palette."""

        target = None
        current = False
        if palette_type == "__special__":
            if palette_name == "Current Colors":
                current = True
                target = {
                    "name": palette_name,
                    "colors": self.view.settings().get('color_helper.file_palette', [])
                }
            elif palette_name == "Favorites":
                target = util.get_favs()
        elif palette_type == "__global__":
            for palette in util.get_palettes():
                if palette_name == palette['name']:
                    target = palette
        elif palette_type == "__project__":
            for palette in util.get_project_palettes(self.view.window()):
                if palette_name == palette['name']:
                    target = palette

        if target is not None:
            template_vars = {
                "legacy": util.LEGACY_CLASS,
                "delete": delete,
                'show_delete_menu': not delete and not current,
                "back": '__colors__' if delete else '__palettes__',
                "palette_type": palette_type,
                "palette_name": target["name"],
                "colors": self.format_colors(target['colors'], target['name'], palette_type, delete)
            }

            if update:
                mdpopups.update_popup(
                    self.view,
                    sublime.load_resource('Packages/ColorHelper/panels/colors.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    template_vars=template_vars,
                    nl2br=False
                )
            else:
                self.view.settings().set('color_helper.popup_active', True)
                self.view.settings().set('color_helper.popup_auto', self.auto)
                mdpopups.show_popup(
                    self.view,
                    sublime.load_resource('Packages/ColorHelper/panels/colors.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars,
                    nl2br=False
                )

    def get_cursor_color(self):
        """Get cursor color."""

        color = None
        alpha = None
        alpha_dec = None
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
            rules = util.get_rules(self.view)
            use_hex_argb = rules.get("use_hex_argb", False) if rules else False
            allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
            for m in util.COLOR_RE.finditer(bfr):
                if ref >= m.start(0) and ref < m.end(0):
                    if m.group('hex_compressed') and 'hex_compressed' not in allowed_colors:
                        continue
                    elif m.group('hexa_compressed') and 'hexa_compressed' not in allowed_colors:
                        continue
                    elif m.group('hex') and 'hex' not in allowed_colors:
                        continue
                    elif m.group('hexa') and 'hexa' not in allowed_colors:
                        continue
                    elif m.group('rgb') and 'rgb' not in allowed_colors:
                        continue
                    elif m.group('rgba') and 'rgba' not in allowed_colors:
                        continue
                    elif m.group('gray') and 'gray' not in allowed_colors:
                        continue
                    elif m.group('graya') and 'graya' not in allowed_colors:
                        continue
                    elif m.group('hsl') and 'hsl' not in allowed_colors:
                        continue
                    elif m.group('hsla') and 'hsla' not in allowed_colors:
                        continue
                    elif m.group('hwb') and 'hwb' not in allowed_colors:
                        continue
                    elif m.group('hwba') and 'hwba' not in allowed_colors:
                        continue
                    elif m.group('webcolors') and 'webcolors' not in allowed_colors:
                        continue
                    color, alpha, alpha_dec = util.translate_color(m, bool(use_hex_argb))
                    break
        return color, alpha, alpha_dec

    def show_color_info(self, update=False):
        """Show the color under the cursor."""

        color, alpha, alpha_dec = self.get_cursor_color()
        template_vars = {
            "legacy": util.LEGACY_CLASS
        }

        if color is not None:
            if alpha is not None:
                color += alpha

            html = []

            html.append(
                self.format_info(color.lower(), template_vars, alpha_dec)
            )

            if update:
                mdpopups.update_popup(
                    self.view,
                    sublime.load_resource('Packages/ColorHelper/panels/info.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    template_vars=template_vars,
                    nl2br=False
                )
            else:
                self.view.settings().set('color_helper.popup_active', True)
                self.view.settings().set('color_helper.popup_auto', self.auto)
                mdpopups.show_popup(
                    self.view,
                    sublime.load_resource('Packages/ColorHelper/panels/info.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    location=-1,
                    max_width=1024,
                    max_height=512,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars,
                    nl2br=False
                )
        elif update:
            self.view.hide_popup()

    def set_sizes(self):
        """Get sizes."""

        self.graphic_size = qualify_settings(ch_settings, 'graphic_size', 'medium')
        top_pad = self.view.settings().get('line_padding_top', 0)
        bottom_pad = self.view.settings().get('line_padding_bottom', 0)
        # Sometimes we strangely get None
        if top_pad is None:
            top_pad = 0
        if bottom_pad is None:
            bottom_pad = 0
        box_height = util.get_line_height(self.view) - int(top_pad + bottom_pad) - 6
        if DISTORTION_FIX:
            sizes = {
                "small": (22, 24, 26),
                "medium": (26, 28, 26),
                "large": (30, 32, 26)
            }
        else:
            sizes = {
                "small": (box_height, box_height, box_height * 2),
                "medium": (int(box_height * 1.5), int(box_height * 1.5), box_height * 2),
                "large": (int(box_height * 2), int(box_height * 2), box_height * 2)
            }
        self.color_h, self.color_w, self.palette_w = sizes.get(
            self.graphic_size,
            sizes["medium"]
        )

    def check_size(self, height):
        """Create checkered size based on height."""

        if DISTORTION_FIX:
            check_size = 2
        else:
            check_size = int((height - (BORDER_SIZE * 2)) / 4)
            if check_size < 2:
                check_size = 2
        return check_size

    def run(self, edit, mode, palette_name=None, color=None, auto=False):
        """Run the specified tooltip."""

        self.set_sizes()
        s = sublime.load_settings('color_helper.sublime-settings')
        use_color_picker_package = s.get('use_color_picker_package', False)
        self.color_picker_package = use_color_picker_package and util.color_picker_available()
        self.no_info = True
        self.no_palette = True
        self.auto = auto
        if mode == "palette":
            self.no_palette = False
            if palette_name is not None:
                self.show_colors(palette_name)
            else:
                self.show_palettes()
        elif mode == "color_picker":
            self.no_info = True
            color, alpha = self.get_cursor_color()[:-1]
            if color is not None:
                if alpha is not None:
                    color += alpha
            else:
                color = '#ffffffff'
            self.color_picker(color)
        elif mode == "color_picker_result":
            self.insert_color(color, picker=True)
        elif mode == "info":
            self.no_info = False
            self.no_palette = False
            self.show_color_info()

    def is_enabled(self, mode, palette_name=None, color=None, auto=False):
        """Check if command is enabled."""

        s = sublime.load_settings('color_helper.sublime-settings')
        return bool(
            (mode == "info" and self.get_cursor_color()[0]) or
            (
                mode == "palette" and (
                    s.get('enable_global_user_palettes', True) or
                    s.get('enable_project_user_palettes', True) or
                    s.get('enable_favorite_palette', True) or
                    s.get('enable_current_file_palette', True) or
                    s.get('enable_project_palette', True)
                )
            ) or
            mode not in ("info", "palette")
        )


class ColorHelperFileIndexCommand(sublime_plugin.TextCommand):
    """Color Helper file index command."""

    def run(self, edit):
        """Run the command."""
        rules = util.get_rules(self.view)
        if rules and util.get_scope(self.view, rules, skip_sel_check=True):
            if ch_file_thread is None or not ch_file_thread.is_alive():
                start_file_index(self.view)
            else:
                sublime.error_message("File indexer is already running!")
        else:
            sublime.error_message('Cannot index colors in this file!')

    def is_enabled(self):
        """Check if command is enabled."""

        s = sublime.load_settings('color_helper.sublime-settings')
        return s.get('enable_current_file_palette', True)


###########################
# Threading
###########################
class ChPreview(object):
    """Color Helper preview with phantoms."""

    def __init__(self):
        """Setup."""

        self.previous_region = sublime.Region(0, 0)

    def on_navigate(self, href, view):
        """Handle color box click."""

        view.sel().clear()
        view.sel().add(sublime.Region(int(href)))
        view.settings().set('color_helper.no_auto', True)
        view.run_command('color_helper', {"mode": "info"})

    def do_search(self, view, force=False):
        """Perform the search for the highlighted word."""

        # Since the plugin has been reloaded, force update.
        global reload_flag
        if reload_flag:
            reload_flag = False
            force = True

        # Calculate size of preview boxes
        settings = view.settings()
        size_offset = int(qualify_settings(ch_settings, 'inline_preview_offset', 0))
        top_pad = view.settings().get('line_padding_top', 0)
        bottom_pad = view.settings().get('line_padding_bottom', 0)
        # Sometimes we strangely get None
        if top_pad is None:
            top_pad = 0
        if bottom_pad is None:
            bottom_pad = 0
        old_box_height = int(settings.get('color_helper.box_height', 0))
        box_height = util.get_line_height(view) - int(top_pad + bottom_pad) + size_offset
        check_size = int((box_height - 4) / 4)
        current_color_scheme = settings.get('color_scheme')

        if check_size < 2:
            check_size = 2

        # If desired preview boxes are different than current,
        # we need to reload the boxes.
        if old_box_height != box_height or current_color_scheme != settings.get('color_helper.color_scheme', ''):
            self.erase_phantoms(view)
            settings.set('color_helper.color_scheme', current_color_scheme)
            settings.set('color_helper.box_height', box_height)
            settings.set('color_helper.preview_meta', {})
            force = True

        # If we don't need to force previews,
        # quit if visible region is the same as last time
        visible_region = view.visible_region()
        if not force and self.previous_region == visible_region:
            return
        self.previous_region = visible_region

        # Get the current preview positions so we don't insert doubles
        preview = settings.get('color_helper.preview_meta', {})

        # Get the rules and use them to get the needed scopes.
        # The scopes will be used to get the searchable regions.
        rules = util.get_rules(view)
        scope = util.get_scope(view, rules, skip_sel_check=True)
        source = []
        if scope:
            for r in view.find_by_selector(scope):
                if r.end() < visible_region.begin():
                    continue
                if r.begin() > visible_region.end():
                    continue
                if r.begin() < visible_region.begin():
                    start = max(visible_region.begin() - 20, 0)
                    if r.end() > visible_region.end():
                        end = min(visible_region.end() + 20, view.size())
                    else:
                        end = r.end()
                    r = sublime.Region(start, end)
                elif r.end() > visible_region.end():
                    r = sublime.Region(r.begin(), min(visible_region.end() + 20, view.size()))
                source.append(r)
        else:
            # Nothing to search for
            self.erase_phantoms(view)

        if source:
            # See what colors are allowed
            self.allowed_colors = set(rules.get('allowed_colors', []))
            use_hex_argb = rules.get('use_hex_argb', False)

            # Find the colors
            colors = []
            for src in source:
                text = view.substr(src)
                for m in util.COLOR_RE.finditer(text):
                    src_start = src.begin() + m.start(0)
                    src_end = src.begin() + m.end(0)
                    position_on_left = preview_is_on_left()
                    pt = src_start if position_on_left else src_end
                    if str(pt) in preview:
                        continue
                    elif not visible_region.contains(sublime.Region(src.begin() + m.start(0), src.begin() + m.end(0))):
                        continue
                    elif m.group('hex_compressed'):
                        if not self.color_okay('hex_compressed'):
                            continue
                        color_type = 'hex_compressed'
                    elif m.group('hexa_compressed'):
                        if not self.color_okay('hexa_compressed'):
                            continue
                        color_type = 'hexa_compressed'
                    elif m.group('hex'):
                        if not self.color_okay('hex'):
                            continue
                        color_type = 'hex'
                    elif m.group('hexa'):
                        if not self.color_okay('hexa'):
                            continue
                        color_type = 'hexa'
                    elif m.group('rgb'):
                        if not self.color_okay('rgb'):
                            continue
                        color_type = 'rgb'
                    elif m.group('rgba'):
                        if not self.color_okay('rgba'):
                            continue
                        color_type = 'rgba'
                    elif m.group('gray'):
                        if not self.color_okay('gray'):
                            continue
                        color_type = 'gray'
                    elif m.group('graya'):
                        if not self.color_okay('graya'):
                            continue
                        color_type = 'graya'
                    elif m.group('hsl'):
                        if not self.color_okay('hsl'):
                            continue
                        color_type = 'hsl'
                    elif m.group('hsla'):
                        if not self.color_okay('hsla'):
                            continue
                        color_type = 'hsla'
                    elif m.group('hwb'):
                        if not self.color_okay('hwb'):
                            continue
                        color_type = 'hwb'
                    elif m.group('hwba'):
                        if not self.color_okay('hwba'):
                            continue
                        color_type = 'hwba'
                    elif m.group('webcolors'):
                        if not self.color_okay('webcolors'):
                            continue
                        color_type = 'webcolors'
                    else:
                        continue
                    color, alpha, alpha_dec = util.translate_color(m, use_hex_argb)
                    color += alpha if alpha is not None else 'ff'
                    no_alpha_color = color[:-2] if len(color) > 7 else color
                    scope = view.scope_name(pt)
                    start_scope = view.scope_name(src_start)
                    end_scope = view.scope_name(src_end - 1)
                    rgba = RGBA(mdpopups.scope2style(view, scope)['background'])
                    rgba.invert()
                    color = '<a href="%d">%s</a>' % (
                        src_start,
                        mdpopups.color_box(
                            [no_alpha_color, color], rgba.get_rgb(),
                            height=box_height, width=box_height,
                            border_size=PREVIEW_BORDER_SIZE, check_size=check_size
                        )
                    )
                    colors.append(
                        (color, pt, hash(m.group(0)), len(m.group(0)), color_type, hash(start_scope + ':' + end_scope))
                    )

            self.add_phantoms(view, colors, preview)
            settings.set('color_helper.preview_meta', preview)

            # The phantoms may have altered the viewable region,
            # so set previous region to the current viewable region
            self.previous_region = sublime.Region(self.previous_region.begin(), view.visible_region().end())

    def add_phantoms(self, view, colors, preview):
        """Add phantoms."""

        for color in colors:
            pid = mdpopups.add_phantom(
                view,
                'color_helper',
                sublime.Region(color[1]),
                color[0],
                0,
                md=False,
                on_navigate=lambda href, view=view: self.on_navigate(href, view)
            )
            preview[str(color[1])] = [color[2], color[3], color[4], color[5], pid]

    def reset_previous(self):
        """Reset previous region."""
        self.previous_region = sublime.Region(0)

    def erase_phantoms(self, view, incremental=False):
        """Erase phantoms."""

        if incremental:
            # Edits can potentially move the position of all the previews.
            # We need to grab the phantom by their id and then apply the color regex
            # on the phantom range +/- some extra characters so we can catch word boundaries.
            # Clear the phantom if any of the follwoing:
            #    - Phantom can't be found
            #    - regex doesn't match
            #    - regex group doesn't match color type
            #    - match doesn't start at the same point
            #    - hash result is wrong
            # Update preview meta data with new results
            old_preview = view.settings().get('color_helper.preview_meta', {})
            position_on_left = preview_is_on_left()
            preview = {}
            for k, v in old_preview.items():
                phantoms = mdpopups.query_phantom(view, v[4])
                pt = phantoms[0].begin() if phantoms else None
                if pt is None:
                    mdpopups.erase_phantom_by_id(view, v[4])
                else:
                    color_start = pt if position_on_left else pt - v[1]
                    color_end = pt + v[1] if position_on_left else pt
                    approx_color_start = color_start - 5
                    if approx_color_start < 0:
                        approx_color_start = 0
                    approx_color_end = color_end + 5
                    if approx_color_end > view.size():
                        approx_color_end = view.size()
                    text = view.substr(sublime.Region(approx_color_start, approx_color_end))
                    m = util.COLOR_RE.search(text)
                    if (
                        not m or
                        not m.group(v[2]) or
                        approx_color_start + m.start(0) != color_start or
                        hash(m.group(0)) != v[0] or
                        v[3] != hash(view.scope_name(color_start) + ':' + view.scope_name(color_end - 1)) or
                        str(pt) in preview
                    ):
                        mdpopups.erase_phantom_by_id(view, v[4])
                    else:
                        preview[str(pt)] = v
            view.settings().set('color_helper.preview_meta', preview)
        else:
            # Obliterate!
            mdpopups.erase_phantoms(view, 'color_helper')
            view.settings().set('color_helper.preview_meta', {})

    def color_okay(self, color_type):
        """Check if color is allowed."""

        return color_type in self.allowed_colors


class ChPreviewThread(threading.Thread):
    """Load up defaults."""

    def __init__(self):
        """Setup the thread."""
        self.reset()
        threading.Thread.__init__(self)

    def reset(self):
        """Reset the thread variables."""
        self.wait_time = 0.12
        self.time = time()
        self.modified = False
        self.ignore_all = False
        self.clear = False
        self.abort = False

    def payload(self, clear=False, force=False):
        """Code to run."""

        self.modified = False
        # Ignore selection and edit events inside the routine
        self.ignore_all = True
        if ch_preview is not None:
            try:
                view = sublime.active_window().active_view()
                if view:
                    if clear:
                        ch_preview.erase_phantoms(view, incremental=True)
                        ch_preview.reset_previous()
                    else:
                        ch_preview.do_search(view, force)
            except Exception:
                print('ColorHelper: \n' + str(traceback.format_exc()))
        self.ignore_all = False
        self.time = time()

    def kill(self):
        """Kill thread."""

        self.abort = True
        while self.is_alive():
            pass
        self.reset()

    def run(self):
        """Thread loop."""

        while not self.abort:
            if not self.ignore_all:
                if (self.modified) is True and time() - self.time > self.wait_time:
                    sublime.set_timeout_async(lambda: self.payload(clear=True), 0)
                elif not self.modified:
                    sublime.set_timeout_async(self.payload, 0)
            sleep(0.5)


class ColorHelperListener(sublime_plugin.EventListener):
    """Color Helper listener."""

    def on_modified(self, view):
        """Flag that we need to show a tooltip or that we need to add phantoms."""

        if self.ignore_event(view):
            return

        if PHANTOM_SUPPORT and ch_preview_thread is not None:
            now = time()
            ch_preview_thread.modified = True
            ch_preview_thread.time = now

        self.on_selection_modified(view)

    def on_selection_modified(self, view):
        """Flag that we need to show a tooltip."""

        if self.ignore_event(view):
            return

        if not ch_thread.ignore_all:
            now = time()
            ch_thread.modified = True
            ch_thread.time = now

    def set_file_scan_rules(self, view):
        """Set the scan rules for the current view."""

        file_name = view.file_name()
        ext = os.path.splitext(file_name)[1].lower() if file_name is not None else None
        s = sublime.load_settings('color_helper.sublime-settings')
        rules = s.get("color_scanning", [])
        syntax = os.path.splitext(view.settings().get('syntax').replace('Packages/', '', 1))[0]
        scan_scopes = []
        incomplete_scopes = []
        allowed_colors = set()
        use_hex_argb = False
        compress_hex = False

        for rule in rules:
            results = []
            base_scopes = rule.get("base_scopes", [])

            if not base_scopes:
                results.append(True)
            else:
                results.append(False)
                for base in rule.get("base_scopes", []):
                    if view.score_selector(0, base):
                        results[-1] = True
                        break

            syntax_files = rule.get("syntax_files", [])
            syntax_filter = rule.get("syntax_filter", "whitelist")
            syntax_okay = bool(
                not syntax_files or (
                    (syntax_filter == "whitelist" and syntax in syntax_files) or
                    (syntax_filter == "blacklist" and syntax not in syntax_files)
                )
            )
            results.append(syntax_okay)

            extensions = [e.lower() for e in rule.get("extensions", [])]
            results.append(True if not extensions or (ext is not None and ext in extensions) else False)

            if False not in results:
                scan_scopes += rule.get("scan_scopes", [])
                incomplete_scopes += rule.get("scan_completion_scopes", [])
                for color in rule.get("allowed_colors", []):
                    if color == "css3":
                        for c in util.CSS3:
                            allowed_colors.add(c)
                    elif color == "css4":
                        for c in util.CSS4:
                            allowed_colors.add(c)
                    elif color == "all":
                        for c in util.ALL:
                            allowed_colors.add(c)
                    else:
                        allowed_colors.add(color)
                if not use_hex_argb and rule.get("use_hex_argb", False):
                    use_hex_argb = True
                if not compress_hex and rule.get("compress_hex_output", False):
                    compress_hex = True
        if scan_scopes or incomplete_scopes:
            view.settings().set(
                'color_helper.scan',
                {
                    "enabled": True,
                    "scan_scopes": scan_scopes,
                    "scan_completion_scopes": incomplete_scopes,
                    "allowed_colors": list(allowed_colors),
                    "use_hex_argb": use_hex_argb,
                    "compress_hex_output": compress_hex,
                    "current_ext": ext,
                    "current_syntax": syntax,
                    "last_updated": ch_last_updated
                }
            )
        else:
            view.settings().set(
                'color_helper.scan',
                {
                    "enabled": False,
                    "current_ext": ext,
                    "current_syntax": syntax,
                    "last_updated": ch_last_updated
                }
            )
            view.settings().set('color_helper.file_palette', [])
            if not unloading and ch_preview_thread is not None:
                view.settings().add_on_change(
                    'color_helper.reload', lambda view=view: self.on_view_settings_change(view)
                )

    def should_update(self, view):
        """Check if an update should be performed."""

        force_update = False
        color_palette_initialized = view.settings().get('color_helper.file_palette', None) is not None
        rules = view.settings().get('color_helper.scan', None)
        if not color_palette_initialized:
            force_update = True
        elif rules:
            last_updated = rules.get('last_updated', None)
            if last_updated is None or last_updated < ch_last_updated:
                force_update = True
            file_name = view.file_name()
            ext = os.path.splitext(file_name)[1].lower() if file_name is not None else None
            old_ext = rules.get('current_ext')
            if ext is None or ext != old_ext:
                force_update = True
            syntax = os.path.splitext(view.settings().get('syntax').replace('Packages/', '', 1))[0]
            old_syntax = rules.get("current_syntax")
            if old_syntax is None or old_syntax != syntax:
                force_update = True
        else:
            force_update = True
        return force_update

    def on_activated(self, view):
        """Run current file scan and/or project scan if not run before."""

        if self.ignore_event(view):
            if view.settings().get('color_helper.preview_meta', {}):
                view.settings().erase('color_helper.preview_meta')
            return

        if self.should_update(view):
            self.set_file_scan_rules(view)
            s = sublime.load_settings('color_helper.sublime-settings')
            show_current_palette = s.get('enable_current_file_palette', True)
            view.settings().set('color_helper.file_palette', [])
            if show_current_palette:
                start_file_index(view)

    def on_view_settings_change(self, view):
        """Post text command event to catch syntax setting."""

        if not unloading:
            settings = view.settings()
            rules = settings.get('color_helper.scan', None)
            if rules:
                syntax = os.path.splitext(settings.get('syntax').replace('Packages/', '', 1))[0]
                old_syntax = rules.get("current_syntax")
                if old_syntax is None or old_syntax != syntax:
                    self.on_activated(view)
                if settings.get('color_scheme') != settings.get('color_helper.color_scheme', ''):
                    settings.erase('color_helper.preview_meta')
                    mdpopups.erase_phantoms(view, 'color_helper')

    def on_post_save(self, view):
        """Run current file scan and/or project scan on save."""

        if self.ignore_event(view):
            if view.settings().get('color_helper.preview_meta', {}):
                view.settings().erase('color_helper.preview_meta')
            return

        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        if self.should_update(view):
            if PHANTOM_SUPPORT:
                view.settings().erase('color_helper.preview_meta')
                mdpopups.erase_phantoms(view, 'color_helper')
            self.set_file_scan_rules(view)
        if show_current_palette:
            start_file_index(view)

    def on_clone(self, view):
        """Run current file scan on clone."""

        if self.ignore_event(view):
            return
        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        if show_current_palette:
            start_file_index(view)

    def ignore_event(self, view):
        """Check if event should be ignored."""

        return view.settings().get('is_widget', False) or ch_thread is None


class ChFileIndexThread(threading.Thread):
    """Load up defaults."""

    def __init__(self, view, source, allowed_colors, use_hex_argb):
        """Setup the thread."""

        self.abort = False
        self.view = view
        self.use_hex_argb = use_hex_argb
        self.allowed_colors = set(allowed_colors) if not isinstance(allowed_colors, set) else allowed_colors
        self.webcolor_names = re.compile(
            r'\b(%s)\b' % '|'.join(
                [name for name in csscolors.name2hex_map.keys()]
            )
        )
        self.source = source
        threading.Thread.__init__(self)

    def update_index(self, view, colors):
        """Code to run."""

        try:
            colors.sort()
            view.settings().set('color_helper.file_palette', colors)
            util.debug('Colors:\n', colors)
            s = sublime.load_settings('color_helper.sublime-settings')
            if s.get('show_index_status', True):
                sublime.status_message('File color index complete...')
        except Exception:
            pass

    def kill(self):
        """Kill thread."""

        self.abort = True
        while self.is_alive():
            pass

    def run(self):
        """Thread loop."""

        if self.source:
            self.index_colors()

    def color_okay(self, color_type):
        """Check if color is allowed."""

        return color_type in self.allowed_colors

    def index_colors(self):
        """Index colors in file."""

        colors = set()
        for m in util.COLOR_RE.finditer(self.source):
            if self.abort:
                break
            if m.group('hex_compressed') and not self.color_okay('hex_compressed'):
                continue
            elif m.group('hexa_compressed') and not self.color_okay('hexa_compressed'):
                continue
            elif m.group('hex') and not self.color_okay('hex'):
                continue
            elif m.group('hexa') and not self.color_okay('hexa'):
                continue
            elif m.group('rgb') and not self.color_okay('rgb'):
                continue
            elif m.group('rgba') and not self.color_okay('rgba'):
                continue
            elif m.group('gray') and not self.color_okay('gray'):
                continue
            elif m.group('graya') and not self.color_okay('graya'):
                continue
            elif m.group('hsl') and not self.color_okay('hsl'):
                continue
            elif m.group('hsla') and not self.color_okay('hsla'):
                continue
            elif m.group('hwb') and not self.color_okay('hwb'):
                continue
            elif m.group('hwba') and not self.color_okay('hwba'):
                continue
            elif m.group('webcolors') and not self.color_okay('webcolors'):
                continue
            color, alpha, alpha_dec = util.translate_color(m, self.use_hex_argb)
            color += alpha if alpha is not None else 'ff'
            if not color.lower().endswith('ff'):
                parts = alpha_dec.split('.')
                dlevel = len(parts[1]) if len(parts) > 1 else None
                if dlevel is not None:
                    color += '@%d' % dlevel
            colors.add(color)
        if not self.abort:
            sublime.set_timeout(
                lambda view=self.view, colors=list(colors): self.update_index(view, colors), 0
            )


class ChThread(threading.Thread):
    """Load up defaults."""

    def __init__(self):
        """Setup the thread."""

        self.reset()
        threading.Thread.__init__(self)

    def reset(self):
        """Reset the thread variables."""

        self.wait_time = 0.12
        self.time = time()
        self.modified = False
        self.ignore_all = False
        self.abort = False
        self.save_palettes = False

    def color_okay(self, allowed_colors, color_type):
        """Check if color is allowed."""

        return color_type in allowed_colors

    def payload(self):
        """Code to run."""

        self.modified = False
        self.ignore_all = True
        window = sublime.active_window()
        view = window.active_view()
        if view.settings().get('color_helper.no_auto', False):
            view.settings().set('color_helper.no_auto', False)
            self.ignore_all = False
            self.time = time()
            return
        s = sublime.load_settings('color_helper.sublime-settings')
        auto_popup = s.get('auto_popup', True)
        if view is not None and auto_popup:
            info = False
            execute = False
            sels = view.sel()
            rules = util.get_rules(view)
            scope = util.get_scope(view, rules)
            insert_scope = util.get_scope_completion(view, rules)
            scope_okay = (
                scope and
                len(sels) == 1 and sels[0].size() == 0 and
                view.score_selector(sels[0].begin(), scope)
            )
            insert_scope_okay = (
                scope_okay or (
                    insert_scope and
                    len(sels) == 1 and sels[0].size() == 0 and
                    view.score_selector(sels[0].begin(), insert_scope)
                )
            )

            if scope_okay or insert_scope_okay:
                allowed_colors = rules.get('allowed_colors', [])
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
                for m in util.COLOR_ALL_RE.finditer(bfr):
                    if ref >= m.start(0) and ref < m.end(0):
                        if (
                            (m.group('hexa_compressed') and self.color_okay(allowed_colors, 'hexa_compressed')) or
                            (m.group('hex_compressed') and self.color_okay(allowed_colors, 'hex_compressed')) or
                            (m.group('hexa') and self.color_okay(allowed_colors, 'hexa')) or
                            (m.group('hex') and self.color_okay(allowed_colors, 'hex')) or
                            (m.group('rgb') and self.color_okay(allowed_colors, 'rgb')) or
                            (m.group('rgba') and self.color_okay(allowed_colors, 'rgba')) or
                            (m.group('gray') and self.color_okay(allowed_colors, 'gray')) or
                            (m.group('graya') and self.color_okay(allowed_colors, 'graya')) or
                            (m.group('hsl') and self.color_okay(allowed_colors, 'hsl')) or
                            (m.group('hsla') and self.color_okay(allowed_colors, 'hsla')) or
                            (m.group('hwb') and self.color_okay(allowed_colors, 'hwb')) or
                            (m.group('hwba') and self.color_okay(allowed_colors, 'hwba')) or
                            (m.group('webcolors') and self.color_okay(allowed_colors, 'webcolors'))
                        ):
                            info = True
                            execute = True
                        break
                    elif ref == m.end(0):
                        if (
                            (
                                m.group('hash') and (
                                    self.color_okay(allowed_colors, 'hex') or
                                    self.color_okay(allowed_colors, 'hexa') or
                                    self.color_okay(allowed_colors, 'hex_compressed') or
                                    self.color_okay(allowed_colors, 'hexa_compressed')
                                )
                            ) or
                            (m.group('rgb_open') and self.color_okay(allowed_colors, 'rgb')) or
                            (m.group('rgba_open') and self.color_okay(allowed_colors, 'rgba')) or
                            (m.group('hsl_open') and self.color_okay(allowed_colors, 'hsl')) or
                            (m.group('hsla_open') and self.color_okay(allowed_colors, 'hsla')) or
                            (
                                m.group('hwb_open') and
                                (
                                    self.color_okay(allowed_colors, 'hwb') or
                                    self.color_okay(allowed_colors, 'hwba')
                                )
                            ) or
                            (
                                m.group('gray_open') and (
                                    self.color_okay(allowed_colors, 'gray') or
                                    self.color_okay(allowed_colors, 'graya')
                                )
                            )
                        ):
                            execute = True
                        break
                if execute:
                    view.run_command('color_helper', {"mode": "palette" if not info else "info", "auto": True})
            if (
                not execute and
                view.settings().get('color_helper.popup_active', False) and
                view.settings().get('color_helper.popup_auto', False)
            ):
                mdpopups.hide_popup(view)
        self.ignore_all = False
        self.time = time()

    def kill(self):
        """Kill thread."""

        self.abort = True
        while self.is_alive():
            pass
        self.reset()

    def run(self):
        """Thread loop."""

        while not self.abort:
            if self.modified is True and time() - self.time > self.wait_time:
                sublime.set_timeout(lambda: self.payload(), 0)
            sleep(0.5)


###########################
# Plugin Initialization
###########################
def settings_reload():
    """Handle settings reload event."""
    global ch_last_updated
    global reload_flag
    reload_flag = True
    ch_last_updated = time()
    setup_previews()


def setup_previews():
    """Setup previews."""

    global ch_preview_thread
    global ch_preview
    global unloading

    if PHANTOM_SUPPORT:
        unloading = True
        if ch_preview_thread is not None:
            ch_preview_thread.kill()
        for w in sublime.windows():
            for v in w.views():
                v.settings().clear_on_change('color_helper.reload')
                v.settings().erase('color_helper.preview_meta')
                mdpopups.erase_phantoms(v, 'color_helper')
        unloading = False

        if ch_settings.get('inline_previews', False):
            ch_preview = ChPreview()
            ch_preview_thread = ChPreviewThread()
            ch_preview_thread.start()


def plugin_loaded():
    """Setup plugin."""

    global ch_settings
    global ch_thread
    global ch_file_thread
    global ch_last_updated

    # Setup settings
    ch_settings = sublime.load_settings('color_helper.sublime-settings')

    # Setup reload events
    ch_settings.clear_on_change('reload')
    ch_settings.add_on_change('reload', settings_reload)
    settings_reload()

    # Start event thread
    if ch_thread is not None:
        ch_thread.kill()
    ch_thread = ChThread()
    ch_thread.start()
    setup_previews()

    # Try and ensure key dependencies are at the latest known good version.
    # This is only done because Package Control does not do this on package upgrade at the present.
    try:
        from package_control import events

        if events.post_upgrade(__pc_name__):
            if not LATEST_SUPPORTED_MDPOPUPS and ch_settings.get('upgrade_dependencies', True):
                window = sublime.active_window()
                if window:
                    window.run_command('satisfy_dependencies')
    except ImportError:
        print('ColorHelper: Could not import Package Control')


def plugin_unloaded():
    """Kill threads."""

    global unloading
    unloading = True

    if ch_thread is not None:
        ch_thread.kill()
    if ch_file_thread is not None:
        ch_file_thread.kill()
    if ch_preview_thread is not None:
        ch_preview_thread.kill()

    # Clear view events
    ch_settings.clear_on_change('reload')
    if PHANTOM_SUPPORT:
        for w in sublime.windows():
            for v in w.views():
                v.settings().clear_on_change('color_helper.reload')

    unloading = False
