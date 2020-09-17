"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
from coloraide.css import SRGB, colorcss_match, colorcss
import re
import mdpopups
from . import color_helper_util as util
from .multiconf import get as qualify_settings
import traceback
from html.parser import HTMLParser
from .color_helper_mixin import _ColorBoxMixin

RE_COLOR_START = re.compile(r"(?i)(?:\bcolor\(|\bhsla?\(|\bgray\(|\blch\(|\blab\(|\bhwb\(|\b(?<!\#)[\w]{3,}(?!\()\b|\#|\brgba?\()")

__pc_name__ = "ColorHelper"

PREVIEW_SCALE_Y = 6
PALETTE_SCALE_X = 8
PALETTE_SCALE_Y = 2
BORDER_SIZE = 1


###########################
# Main Code
###########################
class ColorHelperCommand(_ColorBoxMixin, sublime_plugin.TextCommand):
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

        self.view.run_command('color_helper', {"mode": "palette"})

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
                    height=self.height * PALETTE_SCALE_Y, width=self.palette_w * PALETTE_SCALE_X,
                    border_size=BORDER_SIZE, check_size=self.check_size(self.height)
                ),
                label
            )
        )
        return ''.join(colors)

    def format_colors(self, color_list, label, palette_type, delete=None):
        """Format colors under palette."""

        colors = ['\n## %s\n' % label]
        count = 0

        check_size = self.check_size(self.height)
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
                            self.default_border, height=self.height, width=self.width, border_size=BORDER_SIZE,
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
                            self.default_border, height=self.height, width=self.width, border_size=BORDER_SIZE,
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
                height=self.height * PREVIEW_SCALE_Y, width=self.palette_w * PREVIEW_SCALE_Y,
                border_size=BORDER_SIZE, check_size=self.check_size(self.height * PREVIEW_SCALE_Y)
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

    def run(self, edit, mode, palette_name=None, color=None, auto=False):
        """Run the specified tooltip."""

        s = sublime.load_settings('color_helper.sublime-settings')
        self.setup_image_border()
        self.setup_sizes()
        self.palette_w = self.width * 2
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
