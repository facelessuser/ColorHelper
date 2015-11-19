"""
ColorHelper.

Copyright (c) 2015 Isaac Muse <isaacmuse@gmail.com>
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
from ColorHelper.color_helper_insert import InsertionCalc
# import traceback

PALETTE_MENU = '[palettes](__palettes__){: .color-helper .small} '
PICK_MENU = '[picker](__color_picker__:%s){: .color-helper .small} '
ADD_COLOR_MENU = '[add](__add_color__:%s){: .color-helper .small} '
UNMARK_MENU = '[unmark](__remove_fav__:%s){: .color-helper .small}'
MARK_MENU = '[mark](__add_fav__:%s){: .color-helper .small}'
WEB_COLOR = '''[&gt;&gt;&gt;](__convert__:%s:name){: .color-helper .small} <span class="constant numeric">%s</span>
'''
HEX_COLOR = '''[&gt;&gt;&gt;](__convert__:%s:hex){: .color-helper .small} <span class="support type">%s</span>
'''
RGB_COLOR = '''[&gt;&gt;&gt;](__convert__:%s:rgb){: .color-helper .small} \
<span class="keyword">rgb</span>(<span class="constant numeric">%d, %d, %d</span>)
'''
RGBA_COLOR = '''[&gt;&gt;&gt;](__convert__:%s:rgba){: .color-helper .small} \
<span class="keyword">rgba</span>(<span class="constant numeric">%d, %d, %d, %s</span>)
'''
HSL_COLOR = '''[&gt;&gt;&gt;](__convert__:%s:hsl){: .color-helper .small} \
<span class="keyword">hsl</span>(<span class="constant numeric">%s, %s%%, %s%%</span>)
'''
HSLA_COLOR = '''[&gt;&gt;&gt;](__convert__:%s:hsla){: .color-helper .small} \
<span class="keyword">hsla</span>(<span class="constant numeric">%s, %s%%, %s%%, %s</span>)
'''

BACK_INFO_MENU = '[back](__info__){: .color-helper .small} '
BACK_PALETTE_MENU = '[back](__palettes__){: .color-helper .small} '
BACK_COLORS_MENU = '[back](__colors__:%s:%s){: .color-helper .small} '
DELETE_PALETTE_MENU = '[delete](__delete__palettes__){: .color-helper .small} '
DELETE_COLOR_MENU = '[delete](__delete_colors__:%s:%s){: .color-helper .small} '
DELETE_COLOR = '''
## Delete Color
Click the color to delete.
'''
DELETE_PALETTE = '''
## Delete Palette
Click the palette to delete.
'''
NEW_PALETTE = '''
## New Palette
Click the link or palette to add **%(color)s**{: .keyword}.

[Create New Palette](__create_palette__:__global__:%(color)s)

[Create New Project Palette](__create_palette__:__project__:%(color)s)

---

'''

DIVIDER = '''

---

'''

ch_settings = None

if 'ch_thread' not in globals():
    ch_thread = None

if 'ch_file_thread' not in globals():
    ch_file_thread = None


###########################
# Helper Classes/Functions
###########################
def start_file_index(view):
    """Kick off current file color index."""
    global ch_file_thread
    if view is not None and (ch_file_thread is None or not ch_file_thread.is_alive()):
        scope = util.get_scope(view, skip_sel_check=True)
        if scope:
            source = []
            for r in view.find_by_selector(scope):
                source.append(view.substr(r))
            util.debug('Regions to search:\n', source)
            if len(source):
                ch_file_thread = ChFileIndexThread(view, ' '.join(source))
                ch_file_thread.start()
                sublime.status_message('File color indexer started...')


###########################
# Main Code
###########################
class ColorHelperCommand(sublime_plugin.TextCommand):
    """Color Helper command object."""

    def on_hide(self):
        """Hide popup event."""

        self.view.settings().set('color_helper_popup_active', False)

    def on_navigate(self, href):
        """Handle link clicks."""

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
            self.view.run_command('color_helper_picker', {'color': color})

    def insert_color(self, target_color, convert=None, ch_picker=False):
        """Insert colors."""

        sels = self.view.sel()
        if (len(sels) == 1 and sels[0].size() == 0):
            point = sels[0].begin()
            insert_calc = InsertionCalc(self.view, point, target_color, convert, ch_picker)
            insert_calc.calc()
            if ch_picker:
                target_color = target_color[:-2]
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
                    util.fmt_float(h * 360.0),
                    util.fmt_float(s * 100.0),
                    util.fmt_float(l * 100.0)
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
                mdpopups.color_box(color_list, '#cccccc', '#333333', height=32, width=32 * 8, border_size=2),
                label
            )
        )
        return ''.join(colors)

    def format_colors(self, color_list, label, palette_type, delete=None):
        """Format colors under palette."""

        colors = ['\n## %s\n' % label]
        count = 0
        for f in color_list:
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
                        mdpopups.color_box([f], '#cccccc', '#333333', height=32, width=32, border_size=2),
                        f, palette_type, label,
                    )
                )
            else:
                colors.append(
                    '[%s](%s)' % (
                        mdpopups.color_box([f], '#cccccc', '#333333', height=32, width=32, border_size=2), f
                    )
                )
            count += 1
        return ''.join(colors)

    def format_info(self, color, alpha=None):
        """Format the selected color info."""
        rgba = RGBA(color)

        try:
            web_color = csscolors.hex2name(rgba.get_rgb())
        except Exception:
            web_color = None

        s = sublime.load_settings('color_helper.sublime-settings')
        use_color_picker_package = s.get('use_color_picker_package', False)
        self.color_picker_package = use_color_picker_package and util.color_picker_available()
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
            color_box_wrapper = '\n\n[%s]' + ('(__color_picker__:%s)' % color)
        elif click_color_box_to_pick == 'palette_picker' and palettes_enabled:
            color_box_wrapper = '\n\n[%s](__palettes__)'
        else:
            color_box_wrapper = '\n\n%s'

        info = []

        if click_color_box_to_pick != 'palette_picker' and palettes_enabled:
            info.append(PALETTE_MENU)
        if click_color_box_to_pick != 'color_picker' and show_picker:
            info.append(PICK_MENU % color)
        if show_global_palettes or show_project_palettes:
            info.append(ADD_COLOR_MENU % color.lower())
        if show_favorite_palette:
            if color in util.get_favs()['colors']:
                info.append(UNMARK_MENU % color.lower())
            else:
                info.append(MARK_MENU % color.lower())

        info.append(
            color_box_wrapper % mdpopups.color_box([color], '#cccccc', '#333333', height=64, width=192, border_size=2)
        )

        if show_conversions:
            info.append('\n\n---\n\n')
            if web_color:
                info.append(WEB_COLOR % (color, web_color))
            info.append(HEX_COLOR % (color, (color.lower() if not alpha else color[:-2].lower())))
            info.append(RGB_COLOR % (color, rgba.r, rgba.g, rgba.b))
            info.append(RGBA_COLOR % (color, rgba.r, rgba.g, rgba.b, alpha if alpha else '1'))
            h, l, s = rgba.tohls()
            info.append(
                HSL_COLOR % (color, util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0))
            )
            info.append(
                HSLA_COLOR % (
                    color, util.fmt_float(h * 360.0), util.fmt_float(s * 100.0), util.fmt_float(l * 100.0),
                    alpha if alpha else '1'
                )
            )
        return ''.join(info)

    def show_palettes(self, delete=False, color=None, update=False):
        """Show preview of all palettes."""

        show_div = False
        s = sublime.load_settings('color_helper.sublime-settings')
        show_global_palettes = s.get('enable_global_user_palettes', True)
        show_project_palettes = s.get('enable_project_user_palettes', True)
        show_favorite_palette = s.get('enable_favorite_palette', True)
        show_current_palette = s.get('enable_current_file_palette', True)

        html = []

        if (not self.no_info and not delete) or color:
            html.append(BACK_INFO_MENU)
        elif delete:
            html.append(BACK_PALETTE_MENU)

        if not delete and not color and (show_global_palettes or show_project_palettes or show_favorite_palette):
            html.append(DELETE_PALETTE_MENU)

        if delete:
            html.append(DELETE_PALETTE)

        if color:
            html.append(NEW_PALETTE % {'color': color})

        if show_favorite_palette:
            favs = util.get_favs()
            if len(favs['colors']) or color:
                show_div = True
                html.append(
                    self.format_palettes(favs['colors'], favs['name'], '__special__', delete=delete, color=color)
                )

        if show_current_palette:
            current_colors = self.view.settings().get('color_helper_file_palette', [])
            if not delete and not color and len(current_colors):
                show_div = True
                html.append(
                    self.format_palettes(current_colors, "Current Colors", '__special__', delete=delete, color=color)
                )

        if show_global_palettes:
            palettes = util.get_palettes()
            if len(palettes) and show_div:
                show_div = False
                html.append('\n\n---\n\n')
            for palette in palettes:
                show_div = True
                name = palette.get("name")
                html.append(
                    self.format_palettes(
                        palette.get('colors', []), name, '__global__', palette.get('caption'),
                        delete=delete,
                        color=color
                    )
                )

        if show_project_palettes:
            palettes = util.get_project_palettes(self.view.window())
            if len(palettes) and show_div:
                show_div = False
                html.append(DIVIDER)
            for palette in palettes:
                name = palette.get("name")
                html.append(
                    self.format_palettes(
                        palette.get('colors', []), name, '__project__', palette.get('caption'),
                        delete=delete,
                        color=color
                    )
                )

        if update:
            mdpopups.update_popup(self.view, ''.join(html), css=util.ADD_CSS)
        else:
            self.view.settings().set('color_helper_popup_active', True)
            mdpopups.show_popup(
                self.view,
                ''.join(html), location=-1, max_width=600,
                on_navigate=self.on_navigate,
                on_hide=self.on_hide,
                flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                css=util.ADD_CSS
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
            html = []

            if not delete:
                html.append(BACK_PALETTE_MENU)
                if not current:
                    html.append(DELETE_COLOR_MENU % (palette_type, target['name']))
            else:
                html.append(BACK_COLORS_MENU % (palette_type, target['name']))

            if delete:
                html.append(DELETE_COLOR)

            html.append(
                self.format_colors(target['colors'], target['name'], palette_type, delete)
            )

            if update:
                mdpopups.update_popup(self.view, ''.join(html), css=util.ADD_CSS)
            else:
                self.view.settings().set('color_helper_popup_active', True)
                mdpopups.show_popup(
                    self.view,
                    ''.join(html), location=-1, max_width=600,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    css=util.ADD_CSS
                )

    def show_color_info(self, update=False):
        """Show the color under the cursor."""

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
            for m in util.COLOR_RE.finditer(bfr):
                if ref >= m.start(0) and ref < m.end(0):
                    color, alpha = util.translate_color(m)
                    break
        if color is not None:
            if alpha is not None:
                color += "%02X" % int('%.0f' % (float(alpha) * 255.0))

            html = []

            html.append(
                self.format_info(color.lower(), alpha)
            )

            if update:
                mdpopups.update_popup(self.view, ''.join(html), css=util.ADD_CSS)
            else:
                self.view.settings().set('color_helper_popup_active', True)
                mdpopups.show_popup(
                    self.view,
                    ''.join(html), location=-1, max_width=600,
                    on_navigate=self.on_navigate,
                    on_hide=self.on_hide,
                    flags=sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    css=util.ADD_CSS
                )
        elif update:
            self.view.hide_popup()

    def run(self, edit, mode="palette", palette_name=None, color=None):
        """Run the specified tooltip."""

        self.no_info = True
        if mode == "palette":
            if palette_name is not None:
                self.show_colors(palette_name)
            else:
                self.show_palettes()
        elif mode == "color" and util.is_hex_color(color):
            self.insert_color(color)
        elif mode == "ch_picker":
            self.insert_color(color, ch_picker=True)
        elif mode == "info":
            self.no_info = False
            self.show_color_info()

    def is_enabled(self, mode="palette", palette_name=None, color=None):
        """Check if command is enabled."""

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
    """Color Helper file index command."""

    def run(self, edit):
        """Run the command."""
        if util.get_scope(self.view, skip_sel_check=True):
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
class ColorHelperListener(sublime_plugin.EventListener):
    """Color Helper listener."""

    def on_selection_modified(self, view):
        """Flag that we need to show a tooltip."""

        if ch_thread.ignore_all:
            return
        now = time()
        ch_thread.modified = True
        ch_thread.time = now

    on_modified = on_selection_modified

    def on_activated(self, view):
        """Run current file scan and/or project scan if not run before."""

        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        if show_current_palette and view.settings().get('color_helper_file_palette', None) is None:
            view.settings().set('color_helper_file_palette', [])
            start_file_index(view)

    def on_post_save(self, view):
        """Run current file scan and/or project scan on save."""

        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        if show_current_palette:
            start_file_index(view)

    def on_clone(self, view):
        """Run current file scan on clone."""

        s = sublime.load_settings('color_helper.sublime-settings')
        show_current_palette = s.get('enable_current_file_palette', True)
        if show_current_palette:
            start_file_index(view)


class ChFileIndexThread(threading.Thread):
    """Load up defaults."""

    def __init__(self, view, source):
        """Setup the thread."""

        self.abort = False
        self.view = view
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
            sublime.status_message('File color index complete...')
            view.settings().set('color_helper_file_palette', colors)
            util.debug('Colors:\n', colors)
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

    def index_colors(self):
        """Index colors in file."""

        colors = set()
        for m in util.COLOR_RE.finditer(self.source):
            if self.abort:
                break
            color, alpha = util.translate_color(m)
            if color is not None:
                colors.add(color)
        for m in self.webcolor_names.finditer(self.source):
            if self.abort:
                break
            colors.add(csscolors.name2hex(m.group(0)))
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

    def payload(self):
        """Code to run."""

        self.modified = False
        self.ignore_all = True
        window = sublime.active_window()
        view = window.active_view()
        if view is not None:
            info = False
            execute = False
            sels = view.sel()
            scope = util.get_scope(view)
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
                for m in util.COLOR_ALL_RE.finditer(bfr):
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
            if not execute and view.settings().get('color_helper_popup_active', False):
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
def init_plugin():
    """Setup plugin variables and objects."""

    global ch_settings
    global ch_thread
    global ch_file_thread

    # Make sure cache folder exists
    cache_folder = util.get_cache_dir()
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

    # Setup reload events
    pref_settings = sublime.load_settings('Preferences.sublime-settings')
    pref_settings.clear_on_change('colorhelper_reload')
    ch_settings.clear_on_change('reload')

    # Start event thread
    if ch_thread is not None:
        ch_thread.kill()
    ch_thread = ChThread()
    ch_thread.start()


def plugin_loaded():
    """Setup plugin."""

    init_plugin()


def plugin_unloaded():
    """Kill threads."""

    ch_thread.kill()
    if ch_file_thread is not None:
        ch_file_thread.kill()
