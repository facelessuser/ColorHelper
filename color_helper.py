"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
from coloraide.css import SRGB, HSL, HWB, colorcss_match, colorcss
from coloraide.colors import LCH as GEN_LCH
from coloraide.css.colors import css_names
from coloraide import colors as generic_colors
import threading
from time import time, sleep
import re
import os
import mdpopups
from . import color_helper_util as util
from .multiconf import get as qualify_settings
import traceback
from html.parser import HTMLParser
from queue import Queue
import base64

PREVIEW_IMG = (
    '<style>'
    'html, body {{margin: 0; padding: 0;}} a {{line-height: 0;}}'
    '</style>'
    '<a href="{}"{}>{}</a>'
)

RE_COLOR_START = re.compile(r"(?i)(?:\bcolor\(|\bhsla?\(|\bgray\(|\blch\(|\blab\(|\bhwb\(|\b(?<!\#)[\w]{3,}(?!\()\b|\#|\brgba?\()")

__pc_name__ = "ColorHelper"

PREVIEW_SCALE_Y = 6
PALETTE_SCALE_X = 8
PALETTE_SCALE_Y = 2
BORDER_SIZE = 1
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
                # if len(source):
                #     ch_file_thread = ChFileIndexThread(
                #         view, ' '.join(source),
                #         rules.get('allowed_colors', []),
                #         rules.get('use_hex_argb', False)
                #     )
                #     ch_file_thread.start()
                #     s = sublime.load_settings('color_helper.sublime-settings')
                #     if s.get('show_index_status', True):
                #         sublime.status_message('File color indexer started...')


def preview_is_on_left():
    """Return boolean for positioning preview on left/right."""
    return ch_settings.get('inline_preview_position') != 'right'


###########################
# Main Code
###########################
class ColorHelperCommand(sublime_plugin.TextCommand):
    """Color Helper command object."""

    html_parser = HTMLParser()

    def on_hide(self):
        """Hide popup event."""

        self.view.settings().set('color_helper.popup_active', False)
        self.view.settings().set('color_helper.popup_auto', self.auto)

    def unescape(self, value):
        """Unescape URL."""

        return self.html_parser.unescape(value)

    def on_navigate(self, href):
        """Handle link clicks."""

        if href.startswith('__insert__'):
            parts = href.split(':', 3)
            if len(parts) == 4:
                self.show_insert(parts[1], parts[2], self.unescape(parts[3]))
            else:
                self.show_insert(parts[1], parts[2])
        elif href.startswith('__colors__'):
            parts = href.split(':', 2)
            self.show_colors(parts[1], self.unescape(parts[2]), update=True)
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
            self.show_colors(parts[1], self.unescape(parts[2]), delete=True, update=True)
        elif href.startswith('__delete_color__'):
            parts = href.split(':', 3)
            self.delete_color(parts[1], parts[2], self.unescape(parts[3]))
        elif href == '__delete__palettes__':
            self.show_palettes(delete=True, update=True)
        elif href.startswith('__delete__palette__'):
            parts = href.split(':', 2)
            self.delete_palette(parts[1], self.unescape(parts[2]))
        elif href.startswith('__add_color__'):
            self.show_palettes(color=href.split(':', 1)[1], update=True)
        elif href.startswith('__add_palette_color__'):
            parts = href.split(':', 3)
            self.add_palette(parts[1], parts[2], self.unescape(parts[3]))
        elif href.startswith('__create_palette__'):
            parts = href.split(':', 2)
            self.prompt_palette_name(parts[1], parts[2])
        elif href.startswith('__convert_alpha__'):
            parts = href.split(':', 2)
            self.insert_color(parts[1], parts[2], alpha=True)
        elif href.startswith('__convert__'):
            parts = href.split(':', 1)
            self.insert_color(util.decode_color(parts[1]))

    def repop(self):
        """Setup thread to re-popup tooltip."""

        return
        if ch_thread.ignore_all:
            return
        start_task()
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
        """Add palette."""

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
            space_separator_syntax = set(rules.get("space_separator_syntax", []) if rules else [])
            self.view.run_command(
                'color_helper_picker', {
                    'color': color,
                    'allowed_colors': allowed_colors,
                    'use_hex_argb': use_hex_argb,
                    'compress_hex': compress_hex,
                    'on_done': {'command': 'color_helper', 'args': {'mode': "color_picker_result"}},
                    'on_cancel': on_cancel,
                    'space_separator_syntax': list(space_separator_syntax)
                }
            )

    def insert_color(self, target_color, convert=None, picker=False, alpha=False):
        """Insert colors."""

        sels = self.view.sel()
        if (len(sels) == 1):
            point = sels[0].begin()
            is_replace = point != sels[0].end()
            obj = self.get_cursor_color()
            value = target_color
            repl_region = sublime.Region(obj.start, obj.end)
            if not is_replace:
                self.view.sel().subtract(sels[0])
                self.view.sel().add(repl_region)
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

        color_box = [colorcss(color).convert("srgb").to_string(hex_code=True, alpha=True) for color in color_list[:5]]
        colors.append(
            '[%s](%s)' % (
                mdpopups.color_box(
                    color_list, self.default_border,
                    height=self.color_h * PALETTE_SCALE_Y, width=self.palette_w * PALETTE_SCALE_X,
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
            color = colorcss(f).convert("srgb")
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
                            [color.to_string(hex_code=True, alpha=False), color.to_string(hex_code=True, alpha=True)],
                            self.default_border, height=self.color_h, width=self.color_w, border_size=BORDER_SIZE,
                            check_size=check_size
                        ),
                        f, palette_type, label,
                    )
                )
            else:
                colors.append(
                    '[%s](__insert__:%s:%s:%s)' % (
                        mdpopups.color_box(
                            [color.to_string(hex_code=True, alpha=False), color.to_string(hex_code=True, alpha=True)],
                            self.default_border, height=self.color_h, width=self.color_w, border_size=BORDER_SIZE,
                            check_size=check_size
                        ), f, palette_type, label
                    )
                )
            count += 1
        return ''.join(colors)

    def format_info(self, obj, template_vars):
        """Format the selected color info."""

        color = obj.color
        current = self.view.substr(sublime.Region(obj.start, obj.end))
        rules = util.get_rules(self.view)
        srgb = color.convert('srgb')

        # Store color in normal and generic format.
        template_vars['current_color'] = current
        template_vars['generic_color'] = color.to_string(raw=True)
        # allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
        # use_hex_argb = rules.get("use_hex_argb", False) if rules else None

        s = sublime.load_settings('color_helper.sublime-settings')
        # show_global_palettes = s.get('enable_global_user_palettes', True)
        # show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        # show_current_palette = s.get('enable_current_file_palette', True)
        show_picker = s.get('enable_color_picker', True)
        palettes_enabled = (
            # show_global_palettes or show_project_palettes or
            show_favorite_palette  #.or show_current_palette
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
        # if show_global_palettes or show_project_palettes:
        #     template_vars['show_global_palette_menu'] = True
        if show_favorite_palette:
            template_vars['show_favorite_menu'] = True
            template_vars['is_marked'] = color.to_string(raw=True) in util.get_favs()['colors']

        no_alpha_color = srgb.to_string(hex_code=True, alpha=False)
        template_vars['color_preview'] = (
            mdpopups.color_box(
                [no_alpha_color, srgb.to_string(hex_code=True)], self.default_border,
                height=self.color_h * PREVIEW_SCALE_Y, width=self.palette_w * PREVIEW_SCALE_Y,
                border_size=BORDER_SIZE, check_size=self.check_size(self.color_h * PREVIEW_SCALE_Y)
            )
        )

        show_conversions = s.get('enable_color_conversions', True)
        print(show_conversions)
        if show_conversions:

            output_options = rules.get('output_options')
            outputs = []
            for output in output_options:
                value = color.convert(output["space"]).to_string(**output["options"])
                outputs.append(
                    (
                        util.encode_color(value),
                        value
                    )
                )

            template_vars['outputs'] = outputs
            template_vars['show_conversions'] = True

    def show_insert(self, color, dialog_type, palette_name=None, update=False):
        """Show insert panel."""

        original = color
        color = colorcss(color)

        sels = self.view.sel()
        if color is not None and len(sels) == 1:
            rules = util.get_rules(self.view)

            output_options = rules.get('output_options')
            outputs = []
            for output in output_options:
                value = color.convert(output["space"]).to_string(**output["options"])
                outputs.append(
                    (
                        util.encode_color(value),
                        value
                    )
                )

            template_vars = {
                "dialog_type": dialog_type,
                "palette_name": palette_name,
                "current_color": original,
                "color": color.to_string(raw=True)
            }
            template_vars['outputs'] = outputs

            if update:
                mdpopups.update_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/insert.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    template_vars=template_vars
                )
            else:
                self.view.settings().set('color_helper.popup_active', True)
                self.view.settings().set('color_helper.popup_auto', self.auto)
                mdpopups.show_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/insert.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars
                )

    def show_palettes(self, delete=False, color=None, update=False):
        """Show preview of all palettes."""

        show_div = False
        s = sublime.load_settings('color_helper.sublime-settings')
        # show_global_palettes = s.get('enable_global_user_palettes', True)
        # show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        # show_current_palette = s.get('enable_current_file_palette', True)
        s = sublime.load_settings('color_helper.sublime-settings')
        show_picker = s.get('enable_color_picker', True) and self.no_info
        palettes = util.get_palettes()
        project_palettes = util.get_project_palettes(self.view.window())

        template_vars = {
            "color": (color if color else '#ffffffff'),
            "show_picker_menu": show_picker,
            "show_delete_menu": (
                not delete and not color and (show_favorite_palette)  # show_global_palettes or show_project_palettes or
            ),
            "back_target": "__info__" if (not self.no_info and not delete) or color else "__palettes__",
            "show_delete_ui": delete,
            "show_new_ui": bool(color),
            "show_favorite_palette": show_favorite_palette
            # "show_global_palettes": show_global_palettes and len(palettes),
            # "show_project_palettes": show_project_palettes and len(project_palettes)
        }

        if show_favorite_palette:
            favs = util.get_favs()
            if len(favs['colors']) or color:
                show_div = True
                template_vars['favorite_palette'] = (
                    self.format_palettes(favs['colors'], favs['name'], '__special__', delete=delete, color=color)
                )

        # if show_global_palettes and len(palettes):
        #     if show_div:
        #         template_vars['show_separator'] = True
        #         show_div = False
        #     global_palettes = []
        #     for palette in palettes:
        #         show_div = True
        #         name = palette.get("name")
        #         global_palettes.append(
        #             self.format_palettes(
        #                 palette.get('colors', []), name, '__global__', palette.get('caption'),
        #                 delete=delete,
        #                 color=color
        #             )
        #         )
        #     template_vars['global_palettes'] = global_palettes

        # if show_project_palettes and len(project_palettes):
        #     if show_div:
        #         show_div = False
        #         template_vars['show_project_separator'] = True
        #     proj_palettes = []
        #     for palette in project_palettes:
        #         name = palette.get("name")
        #         proj_palettes.append(
        #             self.format_palettes(
        #                 palette.get('colors', []), name, '__project__', palette.get('caption'),
        #                 delete=delete,
        #                 color=color
        #             )
        #         )
        #         template_vars['project_palettes'] = proj_palettes

        if update:
            mdpopups.update_popup(
                self.view,
                util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/palettes.html'),
                wrapper_class="color-helper content",
                css=util.ADD_CSS,
                template_vars=template_vars
            )
        else:
            self.view.settings().set('color_helper.popup_active', True)
            self.view.settings().set('color_helper.popup_auto', self.auto)
            mdpopups.show_popup(
                self.view,
                util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/palettes.html'),
                wrapper_class="color-helper content",
                css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                on_navigate=self.on_navigate,
                on_hide=self.on_hide,
                flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                template_vars=template_vars
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
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/colors.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    template_vars=template_vars
                )
            else:
                self.view.settings().set('color_helper.popup_active', True)
                self.view.settings().set('color_helper.popup_auto', self.auto)
                mdpopups.show_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/colors.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars
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
            # use_hex_argb = rules.get("use_hex_argb", False) if rules else False
            # allowed_colors = rules.get('allowed_colors', []) if rules else util.ALL
            for m in RE_COLOR_START.finditer(bfr):
                if m:
                    pos = m.start(0)
                    obj = colorcss_match(bfr, start=pos)
                    if obj is not None:
                        pos = obj.end
                        if ref >= obj.start and ref < obj.end:
                            obj.start = start + obj.start
                            obj.end = start + obj.end
                            color = obj
                            break
        return color

    def show_color_info(self, update=False):
        """Show the color under the cursor."""

        color = self.get_cursor_color()
        template_vars = {}

        if color is not None:
            html = []

            html.append(
                self.format_info(color, template_vars)
            )

            if update:
                mdpopups.update_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/info.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    template_vars=template_vars
                )
            else:
                self.view.settings().set('color_helper.popup_active', True)
                self.view.settings().set('color_helper.popup_auto', self.auto)
                mdpopups.show_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/info.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    location=-1,
                    max_width=1024,
                    max_height=512,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars
                )
        elif update:
            self.view.hide_popup()

    def set_sizes(self):
        """Get sizes."""

        self.graphic_size = qualify_settings(ch_settings, 'graphic_size', 'medium')
        self.graphic_scale = qualify_settings(ch_settings, 'graphic_scale', None)
        if not isinstance(self.graphic_scale, (int, float)):
            self.graphic_scale = None
        top_pad = self.view.settings().get('line_padding_top', 0)
        bottom_pad = self.view.settings().get('line_padding_bottom', 0)
        # Sometimes we strangely get None
        if top_pad is None:
            top_pad = 0
        if bottom_pad is None:
            bottom_pad = 0
        box_height = util.get_line_height(self.view) - int(top_pad + bottom_pad) - 6
        if self.graphic_scale is not None:
            box_height = box_height * self.graphic_scale
            self.graphic_size = "small"
        small = max(box_height, 8)
        medium = max(box_height * 1.5, 8)
        large = max(box_height * 2, 8)
        sizes = {
            "small": (int(small), int(small), int(small) * 2),
            "medium": (int(medium), int(medium), int(small) * 2),
            "large": (int(large), int(large), int(small) * 2)
        }
        self.color_h, self.color_w, self.palette_w = sizes.get(
            self.graphic_size,
            sizes["medium"]
        )

    def check_size(self, height):
        """Create checkered size based on height."""

        check_size = int((height - (BORDER_SIZE * 2)) / 8)
        if check_size < 2:
            check_size = 2
        return check_size

    def run(self, edit, mode, palette_name=None, color=None, auto=False):
        """Run the specified tooltip."""

        print('-----running-----')
        rgba = None
        s = sublime.load_settings('color_helper.sublime-settings')
        border_clr = s.get('image_border_color')
        if border_clr is not None:
            try:
                rgba = SRGB(border_clr)
            except Exception:
                pass
        if rgba is None:
            hsl = SRGB(mdpopups.scope2style(self.view, '')['background']).convert("hsl")
            hsl.lightness = hsl.lightness + (20 if hsl.luminance() < 0.5 else -20)
            rgba = hsl.convert("srgb")
        self.default_border = rgba.to_string(hex_code=True)

        self.set_sizes()
        self.color_picker_package = False
        # use_color_picker_package = s.get('use_color_picker_package', False)
        # self.color_picker_package = use_color_picker_package and util.color_picker_available()
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
            self.show_insert(color, '__color_picker__')
        elif mode == "info":
            print('info')
            self.no_info = False
            self.no_palette = False
            self.show_color_info()

    def is_enabled(self, mode, palette_name=None, color=None, auto=False):
        """Check if command is enabled."""

        s = sublime.load_settings('color_helper.sublime-settings')
        return bool(
            (mode == "info" and self.get_cursor_color() is not None) or
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


# class ColorHelperFileIndexCommand(sublime_plugin.TextCommand):
#     """Color Helper file index command."""

#     def run(self, edit):
#         """Run the command."""
#         rules = util.get_rules(self.view)
#         if rules and util.get_scope(self.view, rules, skip_sel_check=True):
#             if ch_file_thread is None or not ch_file_thread.is_alive():
#                 start_file_index(self.view)
#             else:
#                 sublime.error_message("File indexer is already running!")
#         else:
#             sublime.error_message('Cannot index colors in this file!')

#     def is_enabled(self):
#         """Check if command is enabled."""

#         s = sublime.load_settings('color_helper.sublime-settings')
#         return s.get('enable_current_file_palette', True)


###########################
# Threading
###########################
class ChPreview:
    """Color Helper preview with phantoms."""

    def __init__(self):
        """Setup."""

        self.previous_region = sublime.Region(0, 0)

    def on_navigate(self, href, view):
        """Handle color box click."""

        view.sel().clear()
        previews = view.settings().get('color_helper.preview_meta', {})
        for k, v in previews.items():
            if href == v[5]:
                phantoms = view.query_phantom(v[4])
                if phantoms:
                    pt = phantoms[0].begin()
                    view.sel().add(sublime.Region(int(pt) if preview_is_on_left() else int(pt) - int(v[1])))
                    view.settings().set('color_helper.no_auto', True)
                    view.run_command('color_helper', {"mode": "info"})
                break

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

        if check_size < 2:
            check_size = 2

        # If desired preview boxes are different than current,
        # we need to reload the boxes.
        current_color_scheme = settings.get('color_scheme')
        if old_box_height != box_height or current_color_scheme != settings.get('color_helper.color_scheme', ''):
            self.erase_phantoms(view)
            settings.set('color_helper.color_scheme', current_color_scheme)
            settings.set('color_helper.box_height', box_height)
            settings.set('color_helper.preview_meta', {})
            force = True

        # If we don't need to force previews,
        # quit if visible region is the same as last time
        visible_region = view.visible_region()
        position = view.viewport_position()
        dimensions = view.viewport_extent()
        bounds = [
            (position[0], position[0] + dimensions[0] - 1),
            (position[1], position[1] + dimensions[1] - 1)
        ]
        if not force and self.previous_region == visible_region:
            return
        self.previous_region = visible_region
        source = view.substr(visible_region)

        # Get the current preview positions so we don't insert doubles
        preview = settings.get('color_helper.preview_meta', {})

        # Get the rules and use them to get the needed scopes.
        # The scopes will be used to get the searchable regions.

        rules = util.get_rules(view)
        scope = util.get_scope(view, rules, skip_sel_check=True)

        if source and scope:

            # Get preview element colors
            out_of_gamut = colorcss("transparent").to_string(hex_code=True, alph=True)
            out_of_gamut_border = colorcss(view.style().get('redish', "red")).to_string(hex_code=True)
            gamut_style = ch_settings.get('gamut_style', 'lch-chroma')

            # Find the colors
            colors = []
            start = 0
            end = len(source)
            for m in RE_COLOR_START.finditer(source):
                start = m.start()
                obj = colorcss_match(source, start=start)
                if obj is not None:
                    src_start = visible_region.begin() + obj.start
                    src_end = visible_region.begin() + obj.end
                    vector_start = view.text_to_layout(src_start)
                    vector_end = view.text_to_layout(src_end)
                    if not (
                        (
                            (bounds[0][0] <= vector_start[0] <= bounds[0][1]) or
                            (bounds[0][0] <= vector_end[0] <= bounds[0][1])
                        ) and (
                            (bounds[1][0] <= vector_start[1] <= bounds[1][1]) or
                            (bounds[1][0] <= vector_end[1] <= bounds[1][1])
                        )
                    ):
                        continue
                    value = view.score_selector(src_start, scope)
                    if not value:
                        continue
                    text = source[obj.start:obj.end]
                else:
                    continue
                position_on_left = preview_is_on_left()
                pt = src_start if position_on_left else src_end
                if str(pt) in preview:
                    continue
                hsl = colorcss(mdpopups.scope2style(view, view.scope_name(pt))['background']).convert("hsl")
                hsl.lightness = hsl.lightness + (20 if hsl.luminance() < 0.5 else -20)
                preview_border = hsl.convert("srgb").to_string(hex_code=True)
                color = obj.color
                title = ''
                if not color.in_gamut("srgb"):
                    title = ' title="Out of gamut"'
                    if gamut_style in ("lch-chroma", "clip"):
                        srgb = color.convert("srgb", fit_gamut=gamut_style)
                        preview1 = srgb.to_string(hex_code=True, alpha=False)
                        preview2 = srgb.to_string(hex_code=True, alpha=True)
                    else:
                        preview1 = out_of_gamut
                        preview2 = out_of_gamut
                        preview_border = out_of_gamut_border
                else:
                    srgb = color.convert("srgb")
                    preview1 = srgb.to_string(hex_code=True, alpha=False)
                    preview2 = srgb.to_string(hex_code=True, alpha=True)
                start_scope = view.scope_name(src_start)
                end_scope = view.scope_name(src_end - 1)
                preview_id = str(time())
                color = PREVIEW_IMG.format(
                    preview_id,
                    title,
                    mdpopups.color_box(
                        [preview1, preview2], preview_border,
                        height=box_height, width=box_height,
                        border_size=PREVIEW_BORDER_SIZE, check_size=check_size
                    )
                )
                colors.append(
                    (
                        color, pt, hash(text), len(text),
                        obj.color.space(), hash(start_scope + ':' + end_scope),
                        preview_id
                    )
                )

            self.add_phantoms(view, colors, preview)
            settings.set('color_helper.preview_meta', preview)

            # The phantoms may have altered the viewable region,
            # so set previous region to the current viewable region
            self.previous_region = sublime.Region(self.previous_region.begin(), view.visible_region().end())

    def add_phantoms(self, view, colors, preview):
        """Add phantoms."""

        for color in colors:
            pid = view.add_phantom(
                'color_helper',
                sublime.Region(color[1]),
                color[0],
                0,
                on_navigate=lambda href, view=view: self.on_navigate(href, view)
            )
            preview[str(color[1])] = [color[2], color[3], color[4], color[5], pid, color[6]]

    def reset_previous(self):
        """Reset previous region."""
        self.previous_region = sublime.Region(0)

    def erase_phantoms(self, view, incremental=False):
        """Erase phantoms."""

        altered = False
        if incremental:
            # Edits can potentially move the position of all the previews.
            # We need to grab the phantom by their id and then apply the color regex
            # on the phantom range +/- some extra characters so we can catch word boundaries.
            # Clear the phantom if any of the following:
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
                phantoms = view.query_phantom(v[4])
                pt = phantoms[0].begin() if phantoms else None
                if pt is None:
                    view.erase_phantom_by_id(v[4])
                    altered = True
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

                    obj = colorcss_match(text, color_start) is not None
                    if (
                        obj is not None or
                        approx_color_start + obj.start != color_start or
                        hash(m.group(0)) != v[0] or
                        v[3] != hash(view.scope_name(color_start) + ':' + view.scope_name(color_end - 1)) or
                        str(pt) in preview
                    ):
                        view.erase_phantom_by_id(v[4])
                        altered = True
                    else:
                        preview[str(pt)] = v
            view.settings().set('color_helper.preview_meta', preview)
        else:
            # Obliterate!
            view.erase_phantoms('color_helper')
            view.settings().set('color_helper.preview_meta', {})
            altered = True
        if altered:
            self.reset_previous()

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

        if clear:
            self.modified = False
        # Ignore selection and edit events inside the routine
        self.ignore_all = True
        if ch_preview is not None:
            try:
                view = sublime.active_window().active_view()
                if view:
                    if not clear:
                        ch_preview.do_search(view, force)
                    else:
                        ch_preview.erase_phantoms(view, incremental=True)
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
                if self.modified is True and (time() - self.time) > self.wait_time:
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

        if ch_preview_thread is not None:
            now = time()
            ch_preview_thread.modified = True
            ch_preview_thread.time = now

        self.on_selection_modified(view)

    def on_selection_modified(self, view):
        """Flag that we need to show a tooltip."""

        if self.ignore_event(view):
            return

        if not ch_thread.ignore_all:
            start_task()
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
        space_separator_syntax = set()
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
            syntax_filter = rule.get("syntax_filter", "allowlist")
            syntax_okay = bool(
                not syntax_files or (
                    (syntax_filter == "allowlist" and syntax in syntax_files) or
                    (syntax_filter == "blocklist" and syntax not in syntax_files)
                )
            )
            results.append(syntax_okay)

            extensions = [e.lower() for e in rule.get("extensions", [])]
            results.append(True if not extensions or (ext is not None and ext in extensions) else False)

            if False not in results:
                scan_scopes += rule.get("scan_scopes", [])
                incomplete_scopes += rule.get("scan_completion_scopes", [])
                for color in rule.get("allowed_colors", []):
                    if color in ("css3", "css4", "L4"):
                        if color in ("css3",):
                            print("DEPRECATED: '{}' specifier is deprecated, please use 'css4'".format(color))
                        for c in util.LEVEL4:
                            allowed_colors.add(c)
                    elif color == "all":
                        for c in util.ALL:
                            allowed_colors.add(c)
                    else:
                        allowed_colors.add(color)
                outputs = rule.get("output_options", [])
                if not use_hex_argb and rule.get("use_hex_argb", False):
                    use_hex_argb = True
                if not compress_hex and rule.get("compress_hex_output", False):
                    compress_hex = True
                break
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
                    "last_updated": ch_last_updated,
                    "output_options": outputs
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
                    view.erase_phantoms('color_helper')

    def on_post_save(self, view):
        """Run current file scan and/or project scan on save."""

        if self.ignore_event(view):
            if view.settings().get('color_helper.preview_meta', {}):
                view.settings().erase('color_helper.preview_meta')
            return

        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        if self.should_update(view):
            view.settings().erase('color_helper.preview_meta')
            view.erase_phantoms('color_helper')
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


class ChThread(threading.Thread):
    """Load up defaults."""

    def __init__(self):
        """Setup the thread."""

        self.reset()
        self.queue = Queue()
        threading.Thread.__init__(self)

    def reset(self):
        """Reset the thread variables."""

        self.wait_time = 0.12
        self.time = time()
        self.queue = Queue()
        self.modified = False
        self.ignore_all = False
        self.abort = False
        self.save_palettes = False

    def color_okay(self, allowed_colors, color_type):
        """Check if color is allowed."""

        return color_type in allowed_colors

    def payload(self):
        """Code to run."""

        # TODO: Don't kick out right away
        self.modified = False
        return

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
        self.queue.put(True)
        while self.is_alive():
            pass
        self.reset()

    def run(self):
        """Thread loop."""

        task = False
        while not self.abort:
            task = self.queue.get()
            while task and not self.abort:
                if self.modified is True and time() - self.time > self.wait_time:
                    sublime.set_timeout(self.payload, 0)
                    task = False
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


def start_task():
    """Start task."""

    if ch_thread.is_alive():
        ch_thread.queue.put(True)


def setup_previews():
    """Setup previews."""

    global ch_preview_thread
    global ch_preview
    global unloading

    unloading = True
    if ch_preview_thread is not None:
        ch_preview_thread.kill()
    for w in sublime.windows():
        for v in w.views():
            v.settings().clear_on_change('color_helper.reload')
            v.settings().erase('color_helper.preview_meta')
            v.erase_phantoms('color_helper')
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
    for w in sublime.windows():
        for v in w.views():
            v.settings().clear_on_change('color_helper.reload')

    unloading = False
