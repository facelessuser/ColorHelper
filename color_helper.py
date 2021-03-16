"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
from coloraide import Color
from . import os_color_picker
import mdpopups
from . import color_helper_util as util
from html.parser import HTMLParser
from .color_helper_mixin import _ColorMixin

__pc_name__ = "ColorHelper"

PREVIEW_SCALE = 8
PALETTE_SCALE_X = 6
PALETTE_SCALE_Y = 2
BORDER_SIZE = 1


###########################
# Main Code
###########################
class ColorHelperCommand(_ColorMixin, sublime_plugin.TextCommand):
    """Color Helper command object."""

    html_parser = HTMLParser()

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
        elif href.startswith('__tools__'):
            self.show_tools()
        elif href.startswith('__tool__'):
            values = href.split(':', 2)
            color = util.decode_color(values[2]) if len(values) > 2 else None
            self.show_tool(values[1], color)
        elif href.startswith('__edit__'):
            self.edit_color(*(href.split(':', 2)[1:]))
        elif href.startswith('__contrast__'):
            self.contrast_color(href.split(':', 1)[1])
        elif href.startswith('__color_picker__'):
            self.color_picker(href.split(':', 1)[1])
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
                    sublime.error_message("The name of '{}' is already in use!".format(palette_name))
                    return
            color_palettes.append({"name": palette_name, 'colors': [color]})
            util.save_palettes(color_palettes)
        elif palette_type == '__project__':
            color_palettes = util.get_project_palettes(self.view.window())
            for palette in color_palettes:
                if palette_name == palette['name']:
                    sublime.error_message("The name of '{}' is already in use!".format(palette_name))
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

        if self.os_color_picker:
            self.view.hide_popup()
            old_color = Color(color).convert("srgb", fit=True)
            new_color = os_color_picker.pick(old_color)
            if new_color.to_string(**util.HEX_NA) != old_color.to_string(**util.HEX_NA):
                sublime.set_timeout(
                    lambda c=new_color.to_string(**util.COLOR_FULL_PREC): self.view.run_command(
                        "color_helper",
                        {"color": c, 'mode': 'result', 'result_type': '__color_picker__'}
                    ),
                    200
                )
            else:
                sublime.set_timeout(self.show_color_info, 200)
        else:
            if not self.no_info:
                on_cancel = {'command': 'color_helper', 'args': {'mode': "info"}}
            elif not self.no_palette:
                on_cancel = {'command': 'color_helper', 'args': {'mode': "palette"}}
            else:
                on_cancel = None
            self.view.run_command(
                'color_helper_picker', {
                    'color': color,
                    'on_done': {
                        'command': 'color_helper',
                        'args': {'mode': "result", 'result_type': '__color_picker__'}
                    },
                    'on_cancel': on_cancel
                }
            )

    def show_tool(self, tool, raw=None):
        """Show color tool."""

        obj = self.get_cursor_color()
        if obj is None and raw is None:
            return

        mod_name = '.'.join([self.custom_color_class.__module__, self.custom_color_class.__name__])
        is_color_mod = mod_name == "ColorHelper.custom.st_colormod.Color"

        if raw is None:
            color = Color(obj.color).to_string(**util.DEFAULT)
            current = self.view.substr(sublime.Region(obj.start, obj.end))
        elif tool == '__colormod__':
            # We need this unaltered
            color = raw
            current = color
        else:
            color = Color(raw).to_string(**util.DEFAULT)
            current = color

        if tool == "__edit__":
            cmd = "color_helper_edit"
            edit_color = color
        elif tool == "__contrast__":
            cmd = "color_helper_contrast_ratio"
            edit_color = color
        elif tool == "__colormod__":
            cmd = "color_helper_sublime_color_mod"
            edit_color = current if is_color_mod else color
        else:
            return

        if not self.no_info:
            on_cancel = {'command': 'color_helper', 'args': {'mode': "info"}}
        else:
            on_cancel = None

        self.view.run_command(
            cmd,
            {
                'initial': edit_color,
                'on_done': {
                    'command': 'color_helper',
                    'args': {'mode': "result", 'result_type': '__tool__:{}'.format(tool)}
                },
                'on_cancel': on_cancel
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
            if obj is not None:
                repl_region = sublime.Region(obj.start, obj.end)
                sel_start = obj.start
            elif is_replace:
                repl_region = sels[0]
                sel_start = repl_region.begin()
            else:
                sel_start = sels[0].begin()
            self.view.run_command("insert", {"characters": value})
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(sel_start + len(value), sel_start))
        self.view.hide_popup()

    def format_palettes(self, color_list, label, palette_type, caption=None, color=None, delete=False):
        """Format color palette previews."""

        colors = ['\n## {}\n'.format(label)]
        if caption:
            colors.append('{}\n'.format(caption))
        if delete:
            label = '__delete__palette__:{}:{}'.format(palette_type, label)
        elif color:
            label = '__add_palette_color__:{}:{}:{}'.format(color, palette_type, label)
        else:
            label = '__colors__:{}:{}'.format(palette_type, label)

        color_box = []
        for color in color_list[:5]:
            c = Color(color)
            preview = self.get_preview(c)
            color_box.append(preview.preview2)

        colors.append(
            '[{}]({})'.format(
                mdpopups.color_box(
                    color_box, self.default_border,
                    height=self.height * PALETTE_SCALE_Y, width=self.palette_w * PALETTE_SCALE_X,
                    border_size=BORDER_SIZE, check_size=self.check_size(self.height * PALETTE_SCALE_Y)
                ),
                label
            )
        )
        return ''.join(colors)

    def format_colors(self, color_list, label, palette_type, delete=None):
        """Format colors under palette."""

        colors = ['\n## {}\n'.format(label)]
        count = 0

        height = self.height * 2
        width = self.width * 2
        check_size = self.check_size(height)
        for f in color_list:
            color = Color(f)
            if count != 0 and (count % 8 == 0):
                colors.append('\n\n')
            elif count != 0:
                if sublime.platform() == 'windows':
                    colors.append('&nbsp; ')
                else:
                    colors.append('&nbsp;')

            preview = self.get_preview(color)
            message = color.to_string(**util.DEFAULT)
            if preview.message:
                message += ' ({})'.format(preview.message)

            if delete:
                colors.append(
                    '[{}](__delete_color__:{}:{}:{} "{}")'.format(
                        mdpopups.color_box(
                            [preview.preview1, preview.preview2],
                            preview.border, height=height, width=width, border_size=BORDER_SIZE,
                            check_size=check_size
                        ),
                        f, palette_type, label, message
                    )
                )
            else:
                colors.append(
                    '[{}](__insert__:{}:{}:{} "{}")'.format(
                        mdpopups.color_box(
                            [preview.preview1, preview.preview2],
                            preview.border, height=height, width=width, border_size=BORDER_SIZE,
                            check_size=check_size
                        ), f, palette_type, label, message
                    )
                )
            count += 1
        return ''.join(colors)

    def format_info(self, obj, template_vars):
        """Format the selected color info."""

        s = sublime.load_settings('color_helper.sublime-settings')

        color = obj.color
        current = self.view.substr(sublime.Region(obj.start, obj.end))

        # Store color in normal and generic format.
        template_vars['current_color'] = util.html_encode(current)
        template_vars['generic_color'] = color.to_string(**util.COLOR_FULL_PREC)
        template_vars['mark_color'] = color.to_string(**util.COLOR)
        template_vars['edit'] = '__colormod__' if self.edit_mode == "st-colormod" else '__edit__'

        show_global_palettes = s.get('enable_global_user_palettes', True)
        show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        show_picker = s.get('enable_color_picker', True)
        palettes_enabled = (
            show_global_palettes or show_project_palettes or
            show_favorite_palette
        )
        click_color_box_to_pick = s.get('click_color_box_to_pick', 'none')

        template_vars['edit_mode'] = self.edit_mode
        if click_color_box_to_pick == 'color_picker' and show_picker:
            template_vars['click_color_picker'] = True
        elif click_color_box_to_pick == 'palette_picker' and palettes_enabled:
            template_vars['click_palette_picker'] = True
        elif click_color_box_to_pick == "edit":
            template_vars['click_color_edit'] = True

        if click_color_box_to_pick != 'palette_picker' and palettes_enabled:
            template_vars['show_palette_menu'] = True
        if click_color_box_to_pick != 'color_picker' and show_picker:
            template_vars['show_picker_menu'] = True

        if show_global_palettes or show_project_palettes:
            template_vars['show_global_palette_menu'] = True
        if show_favorite_palette:
            template_vars['show_favorite_menu'] = True
            template_vars['is_marked'] = color.to_string(**util.COLOR) in util.get_favs()['colors']

        preview = self.get_preview(color)
        message = ''
        if preview.message:
            message = '<p class="small">* {}</p>'.format(preview.message)
        template_vars['color_preview'] = (
            mdpopups.color_box(
                [preview.preview1, preview.preview2], preview.border,
                height=self.height * PREVIEW_SCALE, width=self.width * PREVIEW_SCALE,
                border_size=BORDER_SIZE, check_size=self.check_size(self.height * PREVIEW_SCALE, scale=8)
            )
        )
        template_vars['color_preview_message'] = message

    def show_insert(self, color, dialog_type, palette_name=None, update=False, raw=None):
        """Show insert panel."""

        original = color
        color = Color(color)

        sels = self.view.sel()
        if color is not None and len(sels) == 1:
            outputs = []
            if raw is not None:
                outputs.append((util.encode_color(raw), util.html_encode(raw)))
            custom = self.custom_color_class(color)
            for output in self.output_options:
                params = output.get("format", {})
                value = custom.convert(output["space"]).to_string(**params)
                outputs.append(
                    (
                        util.encode_color(value),
                        util.html_encode(value)
                    )
                )

            template_vars = {
                "dialog_type": dialog_type,
                "palette_name": palette_name,
                "current_color": original,
                "tool_color": util.encode_color(raw if raw else color.to_string(**util.COLOR_FULL_PREC))
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
                mdpopups.show_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/insert.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                    on_navigate=self.on_navigate,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars
                )

    def show_tools(self):
        """Show tools."""

        template_vars = {}
        template_vars["back_target"] = "__info__"
        template_vars['tools'] = [
            ('Edit and Mix', '__tool__:__edit__'),
            ('Contrast', '__tool__:__contrast__'),
            ('Sublime ColorMod', '__tool__:__colormod__')
        ]

        mdpopups.show_popup(
            self.view,
            util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/tools.html'),
            wrapper_class="color-helper content",
            css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
            on_navigate=self.on_navigate,
            flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
            template_vars=template_vars
        )

    def show_palettes(self, delete=False, color=None, update=False):
        """Show preview of all palettes."""

        show_div = False
        s = sublime.load_settings('color_helper.sublime-settings')
        show_global_palettes = s.get('enable_global_user_palettes', True)
        show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        # show_current_palette = s.get('enable_current_file_palette', True)
        s = sublime.load_settings('color_helper.sublime-settings')
        show_picker = s.get('enable_color_picker', True) and self.no_info
        palettes = util.get_palettes()
        project_palettes = util.get_project_palettes(self.view.window())

        template_vars = {
            "color": (Color(color if color else '#ffffffff').to_string(**util.DEFAULT)),
            "show_picker_menu": show_picker,
            "show_delete_menu": (
                not delete and not color and (show_favorite_palette or show_global_palettes or show_project_palettes)
            ),
            "back_target": "__info__" if (not self.no_info and not delete) or color else "__palettes__",
            "show_delete_ui": delete,
            "show_new_ui": bool(color),
            "show_favorite_palette": show_favorite_palette,
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
            proj_palettes = []
            for palette in project_palettes:
                name = palette.get("name")
                proj_palettes.append(
                    self.format_palettes(
                        palette.get('colors', []), name, '__project__', palette.get('caption'),
                        delete=delete,
                        color=color
                    )
                )
                template_vars['project_palettes'] = proj_palettes

        if update:
            mdpopups.update_popup(
                self.view,
                util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/palettes.html'),
                wrapper_class="color-helper content",
                css=util.ADD_CSS,
                template_vars=template_vars
            )
        else:
            mdpopups.show_popup(
                self.view,
                util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/palettes.html'),
                wrapper_class="color-helper content",
                css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                on_navigate=self.on_navigate,
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
                mdpopups.show_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/colors.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS, location=-1, max_width=1024, max_height=512,
                    on_navigate=self.on_navigate,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars
                )

    def get_cursor_color(self):
        """Get cursor color."""

        sels = self.view.sel()
        obj = None
        if (len(sels) == 1 and sels[0].size()):
            region = sels[0]
            bfr = self.view.substr(region)
            obj = self.custom_color_class.match(bfr, fullmatch=True, filters=self.filters)
            if obj is not None:
                obj.start = region.begin()
                obj.end = region.end()
                obj.color = Color(obj.color)
        return obj

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
                mdpopups.show_popup(
                    self.view,
                    util.FRONTMATTER + sublime.load_resource('Packages/ColorHelper/panels/info.html'),
                    wrapper_class="color-helper content",
                    css=util.ADD_CSS,
                    location=-1,
                    max_width=1024,
                    max_height=512,
                    on_navigate=self.on_navigate,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    template_vars=template_vars
                )
        elif update:
            self.view.hide_popup()

    def run(self, edit, mode, palette_name=None, color=None, insert_raw=None, result_type=None):
        """Run the specified tooltip."""

        self.setup_gamut_style()
        self.setup_image_border()
        self.setup_sizes()
        self.setup_color_class()
        self.palette_w = self.width * 2
        s = sublime.load_settings('color_helper.sublime-settings')
        self.os_color_picker = s.get('use_os_color_picker', False)
        self.no_info = True
        self.no_palette = True
        if mode == "palette":
            self.no_palette = False
            if palette_name is not None:
                self.show_colors(palette_name)
            else:
                self.show_palettes()
        elif mode == "color_picker":
            self.no_info = True
            obj = self.get_cursor_color()
            if obj is None:
                color = Color("white", filters=util.SRGB_SPACES).to_string(**util.COLOR_FULL_PREC)
            else:
                color = obj.color.to_string(**util.COLOR_FULL_PREC)
            self.color_picker(color)
        elif mode == "result":
            self.show_insert(color, result_type, raw=insert_raw)
        elif mode == "info":
            self.no_info = False
            self.no_palette = False
            self.show_color_info()

    def is_enabled(self, mode, **kwargs):
        """Check if command is enabled."""

        try:
            # This will throw an exception if there is no rule associated with the view.
            # Can't enable if the view has no color rules.
            self.setup_color_class()
        except Exception:
            return False

        s = sublime.load_settings('color_helper.sublime-settings')
        return bool(
            (mode == "info" and self.get_cursor_color() is not None) or
            (
                mode == "palette" and (
                    s.get('enable_global_user_palettes', True) or
                    s.get('enable_project_user_palettes', True) or
                    s.get('enable_favorite_palette', True) or
                    s.get('enable_project_palette', True)
                )
            ) or
            mode not in ("info", "palette")
        )
