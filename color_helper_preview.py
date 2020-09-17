"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
from coloraide.css import colorcss_match, colorcss
import threading
from time import time, sleep
import re
import os
import mdpopups
from . import color_helper_util as util
import traceback
from .multiconf import get as qualify_settings

PREVIEW_IMG = (
    '<style>'
    'html, body {{margin: 0; padding: 0;}} a {{line-height: 0;}}'
    '</style>'
    '<a href="{}"{}>{}</a>'
)

PREVIEW_BORDER_SIZE = 1

RE_COLOR_START = re.compile(r"(?i)(?:\bcolor\(|\bhsla?\(|\bgray\(|\blch\(|\blab\(|\bhwb\(|\b(?<!\#)[\w]{3,}(?!\()\b|\#|\brgba?\()")

reload_flag = False
ch_last_updated = None
ch_settings = None
unloading = False

if 'ch_preview_thread' not in globals():
    ch_preview_thread = None


def preview_is_on_left():
    """Return boolean for positioning preview on left/right."""
    return ch_settings.get('inline_preview_position') != 'right'


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

    def calculate_box_size(self, view):
        """Calculate the preview box size."""

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
        box_height = util.get_line_height(view) - int(top_pad + bottom_pad) + size_offset
        return box_height

    def do_search(self, view, force=False):
        """Perform the search for the highlighted word."""

        # Since the plugin has been reloaded, force update.
        global reload_flag
        if reload_flag:
            reload_flag = False
            force = True

        # Calculate size of preview boxes
        box_height = self.calculate_box_size(view)
        check_size = int((box_height - 4) / 4)
        if check_size < 2:
            check_size = 2

        # If desired preview boxes are different than current,
        # we need to reload the boxes.
        settings = view.settings()
        old_box_height = int(settings.get('color_helper.box_height', 0))
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
                # Test if we have found a valid color
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

                # Calculate point at which we which to insert preview
                position_on_left = preview_is_on_left()
                pt = src_start if position_on_left else src_end
                if str(pt) in preview:
                    continue

                # Calculate a reasonable border color for our image at this location and get color strings
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

                # Create preview
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

            # Add all previews
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

    def ignore_event(self, view):
        """Check if event should be ignored."""

        return view.settings().get('is_widget', False)


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
    global ch_last_updated

    # Setup settings
    ch_settings = sublime.load_settings('color_helper.sublime-settings')

    # Setup reload events
    ch_settings.clear_on_change('reload')
    ch_settings.add_on_change('reload', settings_reload)
    settings_reload()

    # Start event thread
    setup_previews()


def plugin_unloaded():
    """Kill threads."""

    global unloading
    unloading = True

    if ch_preview_thread is not None:
        ch_preview_thread.kill()

    # Clear view events
    ch_settings.clear_on_change('reload')
    for w in sublime.windows():
        for v in w.views():
            v.settings().clear_on_change('color_helper.reload')

    unloading = False
