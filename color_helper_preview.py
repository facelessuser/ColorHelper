"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
from coloraide.css import Color
import threading
from time import time, sleep
import re
import os
import mdpopups
from . import color_helper_util as util
import traceback
from .multiconf import get as qualify_settings
import importlib
from collections import namedtuple

PREVIEW_IMG = (
    '<style>'
    'html, body {{margin: 0; padding: 0;}} a {{line-height: 0;}}'
    '</style>'
    '<a href="{}"{}>{}</a>'
)

PREVIEW_BORDER_SIZE = 1

RE_COLOR_START = r"(?i)(?:\b(?:color|hsla?|gray|lch|lab|hwb|rgba?)\(|\b(?<!\#)[\w]{3,}(?!\()\b|\#)"

reload_flag = False
ch_last_updated = None
ch_settings = None
unloading = False

if 'ch_preview_thread' not in globals():
    ch_preview_thread = None


def preview_is_on_left():
    """Return boolean for positioning preview on left/right."""
    return ch_settings.get('inline_preview_position') != 'right'


class ColorSwatch(namedtuple('ColorSwatch', ['start', 'end', 'pid', 'timestamp'])):
    """Color swatch."""


class ColorHelperPreviewCommand(sublime_plugin.TextCommand):
    """Color Helper preview with phantoms."""

    def __init__(self, view):
        """Setup."""

        super().__init__(view)
        self.previous_region = sublime.Region(0, 0)
        self.previews = {}
        view.erase_phantoms("color_helper")

    def on_navigate(self, href):
        """Handle color box click."""

        self.view.sel().clear()
        for k, v in self.previews.items():
            if href == v.timestamp:
                phantom = self.view.query_phantom(v.pid)
                if phantom:
                    self.view.sel().add(sublime.Region(int(v.start)))
                    self.view.run_command('color_helper', {"mode": "info"})
                break

    def calculate_box_size(self):
        """Calculate the preview box size."""

        # Calculate size of preview boxes
        settings = self.view.settings()
        size_offset = int(qualify_settings(ch_settings, 'inline_preview_offset', 0))
        top_pad = settings.get('line_padding_top', 0)
        bottom_pad = settings.get('line_padding_bottom', 0)
        # Sometimes we strangely get None
        if top_pad is None:
            top_pad = 0
        if bottom_pad is None:
            bottom_pad = 0
        box_height = util.get_line_height(self.view) - int(top_pad + bottom_pad) + size_offset
        return box_height

    def do_search(self, force=False):
        """
        Perform the search for the highlighted word.

        TODO: This function is a big boy. We should look into breaking it up.
              With that said, this is low priority.
        """

        # Since the plugin has been reloaded, force update.
        global reload_flag
        if reload_flag:
            reload_flag = False
            force = True

        # Calculate size of preview boxes
        box_height = self.calculate_box_size()
        check_size = int((box_height - 2) / 4)
        if check_size < 2:
            check_size = 2

        # If desired preview boxes are different than current,
        # we need to reload the boxes.
        settings = self.view.settings()
        old_box_height = int(settings.get('color_helper.box_height', 0))
        current_color_scheme = settings.get('color_scheme')
        if (
            force or old_box_height != box_height or
            current_color_scheme != settings.get('color_helper.color_scheme', '')
        ):
            self.erase_phantoms()
            settings.set('color_helper.color_scheme', current_color_scheme)
            settings.set('color_helper.box_height', box_height)
            force = True

        # If we don't need to force previews,
        # quit if visible region is the same as last time
        visible_region = self.view.visible_region()
        position = self.view.viewport_position()
        dimensions = self.view.viewport_extent()
        bounds = [
            (position[0], position[0] + dimensions[0] - 1),
            (position[1], position[1] + dimensions[1] - 1)
        ]
        if not force and self.previous_region == visible_region:
            return
        self.previous_region = visible_region
        source = self.view.substr(visible_region)

        # Setup "preview on select"
        preview_on_select = ch_settings.get("preview_on_select", False)
        show_preview = True
        if preview_on_select and len(self.view.sel()) != 1:
            show_preview = False
        elif preview_on_select:
            sel = self.view.sel()[0]

        # Get the rules and use them to get the needed scopes.
        # The scopes will be used to get the searchable regions.
        rules = util.get_rules(self.view)
        # Bail if this if this view has no valid rule or scanning is disabled.
        if rules is None or not rules.get("enabled", False) or not rules.get("allow_scanning", True):
            return
        # Get the scan scopes
        scope = util.get_scope(self.view, rules, skip_sel_check=True)

        if show_preview and source and scope:
            # Get out of gamut related options
            out_of_gamut = Color("transparent").to_string(**util.HEX)
            out_of_gamut_border = Color(self.view.style().get('redish', "red")).to_string(**util.HEX)
            preferred_gamut_mapping = ch_settings.get("preferred_gamut_mapping", "lch-chroma")
            if preferred_gamut_mapping not in ("lch-chroma", "clip"):
                preferred_gamut_mapping = "lch-chroma"
            show_out_of_gamut_preview = ch_settings.get('show_out_of_gamut_preview', True)

            # Get triggers that identify where colors are likely
            color_trigger = re.compile(rules.get("color_trigger", RE_COLOR_START))

            # Get custom color class
            module, color_class = rules.get("color_class", "coloraide.css.colors.Color").rsplit('.', 1)
            filters = rules.get("filters", [])
            color_class = getattr(importlib.import_module(module), color_class)

            # Find the colors
            colors = []
            start = 0
            for m in color_trigger.finditer(source):
                # Test if we have found a valid color
                start = m.start()
                obj = color_class.match(source, start=start, filters=filters)
                if obj is not None:
                    # Calculate visible viewport
                    src_start = visible_region.begin() + obj.start
                    src_end = visible_region.begin() + obj.end
                    vector_start = self.view.text_to_layout(src_start)
                    vector_end = self.view.text_to_layout(src_end)
                    region = sublime.Region(src_start, src_end)

                    # Check if within visible view
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

                    # If "preview on select" is enabled, only show preview if within a selection
                    # or if the selection as no width and the color comes right after.
                    if (
                        preview_on_select and
                        not(sel.empty() and sel.begin() == region.begin()) and
                        not region.intersects(sel)
                    ):
                        continue

                    # Check if the first point within the color matches our scope rules
                    value = self.view.score_selector(src_start, scope)
                    if not value:
                        continue
                else:
                    continue

                # Calculate point at which we which to insert preview
                position_on_left = preview_is_on_left()
                pt = src_start if position_on_left else src_end
                if str(region.begin()) in self.previews:
                    # Already exists
                    continue

                # Calculate a reasonable border color for our image at this location and get color strings
                hsl = Color(
                    mdpopups.scope2style(self.view, self.view.scope_name(pt))['background'],
                    filters=util.SRGB_SPACES
                ).convert("hsl")
                hsl.lightness = hsl.lightness + (30 if hsl.luminance() < 0.5 else -30)
                preview_border = hsl.convert("srgb", fit=preferred_gamut_mapping).to_string(**util.HEX)

                color = Color(obj.color)
                title = ''
                if not color.in_gamut("srgb"):
                    title = ' title="Out of gamut"'
                    if show_out_of_gamut_preview:
                        srgb = color.convert("srgb", fit=preferred_gamut_mapping)
                        preview1 = srgb.to_string(**util.HEX_NA)
                        preview2 = srgb.to_string(**util.HEX)
                    else:
                        preview1 = out_of_gamut
                        preview2 = out_of_gamut
                        preview_border = out_of_gamut_border
                else:
                    srgb = color.convert("srgb")
                    preview1 = srgb.to_string(**util.HEX_NA)
                    preview2 = srgb.to_string(**util.HEX)

                # Create preview
                timestamp = str(time())
                html = PREVIEW_IMG.format(
                    timestamp,
                    title,
                    mdpopups.color_box(
                        [preview1, preview2], preview_border,
                        height=box_height, width=box_height,
                        border_size=PREVIEW_BORDER_SIZE, check_size=check_size
                    )
                )
                colors.append(
                    (
                        html,
                        pt,
                        region.begin(),
                        region.end(),
                        timestamp
                    )
                )

            # Add all previews
            self.add_phantoms(colors)

            # The phantoms may have altered the viewable region,
            # so set previous region to the current viewable region
            self.previous_region = sublime.Region(self.previous_region.begin(), self.view.visible_region().end())

    def add_phantoms(self, colors):
        """Add phantoms."""

        for html, pt, start, end, timestamp in colors:
            pid = self.view.add_phantom(
                'color_helper',
                sublime.Region(pt),
                html,
                0,
                on_navigate=self.on_navigate
            )
            self.previews[str(start)] = ColorSwatch(start, end, pid, timestamp)

    def reset_previous(self):
        """Reset previous region."""
        self.previous_region = sublime.Region(0)

    def erase_phantoms(self):
        """Erase phantoms."""

        # Obliterate!
        self.view.erase_phantoms('color_helper')
        self.previews.clear()
        self.reset_previous()

    def run(self, edit, clear=False, force=False):
        """Run."""

        if ch_preview_thread.ignore_all:
            return
        else:
            ch_preview_thread.ignore_all = True

        try:
            if clear:
                self.erase_phantoms()
            else:
                self.do_search(force)
        except Exception:
            self.erase_phantoms()
            util.debug('ColorHelper: \n' + str(traceback.format_exc()))
        ch_preview_thread.ignore_all = False
        ch_preview_thread.time = time()


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
        self.force = False
        self.ignore_all = False
        self.abort = False
        self.scroll = False
        self.last_view = (-1, -1)
        self.scroll_view = None

    def scroll_check(self):
        """Check if we should issue a scroll event."""

        view = sublime.active_window().active_view()
        vid = view.id()
        wid = -1
        w = view.window()
        if w is not None:
            wid = w.id()
        this_scroll = (wid, vid)
        if self.last_view != this_scroll:
            self.last_view = this_scroll
            self.scroll = True
        elif view.visible_region() != self.scroll_view:
            self.scroll = True
            self.scroll_view = view.visible_region()
            self.time = time()

    def payload(self):
        """Code to run."""

        if not self.ignore_all:
            clear = False
            force = False
            if self.modified:
                clear = True
                self.modified = False
                self.scroll = False
                if self.force:
                    force = True
                    self.force = False
            elif self.force:
                force = True
                self.force = False
                self.modified = False
                self.scroll = False
            else:
                self.scroll = False

            # Ignore selection and edit events inside the routine
            try:
                view = sublime.active_window().active_view()
                args = {"clear": clear, "force": force}
                view.run_command('color_helper_preview', args)
            except Exception:
                util.debug('ColorHelper: \n' + str(traceback.format_exc()))

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
                if (
                    (self.modified is True or self.scroll is True or self.force is True) and
                    (time() - self.time) > self.wait_time
                ):
                    sublime.set_timeout_async(self.payload, 0)
                else:
                    sublime.set_timeout_async(self.scroll_check, 0)
            sleep(0.5)


class ColorHelperListener(sublime_plugin.EventListener):
    """Color Helper listener."""

    def on_modified(self, view):
        """Flag that we need to show a tooltip or that we need to add phantoms."""

        if self.ignore_event(view):
            return

        if ch_preview_thread is not None:
            ch_preview_thread.modified = True
            ch_preview_thread.time = time()

    def on_selection_modified(self, view):
        """Flag that we need to show a tooltip."""
        if self.ignore_event(view):
            return

        if ch_preview_thread is not None and ch_settings.get("preview_on_select", False):
            # We only render previews when things change or a scroll occurs.
            # On selection, we just need to force the change.
            ch_preview_thread.time = time()
            ch_preview_thread.force = True

    def on_activated(self, view):
        """On activated."""

        if self.ignore_event(view):
            return

        if self.should_update(view):
            ch_preview_thread.modified = True
            ch_preview_thread.time = time()
            self.set_file_scan_rules(view)

    def set_file_scan_rules(self, view):
        """Set the scan rules for the current view."""

        if ch_preview_thread:
            ch_preview_thread.ignore_all = True

        view.settings().clear_on_change('color_helper.reload')

        file_name = view.file_name()
        ext = os.path.splitext(file_name)[1].lower() if file_name is not None else None
        s = sublime.load_settings('color_helper.sublime-settings')
        rules = s.get("color_rules", [])
        syntax = os.path.splitext(view.settings().get('syntax').replace('Packages/', '', 1))[0]

        # Check if view meets critera for on of our rule sets
        matched = False
        for rule in rules:
            results = []

            # Check if enabled.
            if not rule.get("enabled", True):
                continue

            # Does the base scope match?
            passed = True
            base_scopes = rule.get("base_scopes", [])
            if base_scopes:
                passed = False
                results.append(False)
                for base in rule.get("base_scopes", []):
                    if view.score_selector(0, base):
                        passed = True
                        break
            if not passed:
                continue

            # Does the syntax match?
            syntax_files = rule.get("syntax_files", [])
            syntax_filter = rule.get("syntax_filter", "allowlist")
            syntax_okay = bool(
                not syntax_files or (
                    (syntax_filter == "allowlist" and syntax in syntax_files) or
                    (syntax_filter == "blocklist" and syntax not in syntax_files)
                )
            )
            if not syntax_okay:
                continue

            # Does the extension match?
            extensions = [e.lower() for e in rule.get("extensions", [])]
            passed = not extensions or (ext is not None and ext in extensions)
            if not passed:
                continue

            # Gather options if rule matches
            scan_scopes = rule.get("scan_scopes", [])
            allow_scanning = rule.get("allow_scanning", True) and scan_scopes
            outputs = rule.get("output_options", util.DEF_OUTPUT)
            colorclass = rule.get("color_class", "coloraide.css.Color")
            color_trigger = rule.get("color_trigger", RE_COLOR_START)
            filters = rule.get("filters", [])
            matched = True
            break

        # Couldn't find any explicit options, so associate a generic  option set to allow basic functionality..
        if not matched:
            generic = s.get("generic", {})
            scan_scopes = generic.get("scan_scopes", [])
            allow_scanning = generic.get("allow_scanning", True) and scan_scopes
            outputs = generic.get("output_options", util.DEF_OUTPUT)
            colorclass = generic.get("color_class", "coloraide.css.Color")
            color_trigger = generic.get("color_trigger", RE_COLOR_START)
            filters = rule.get("filters", [])
            matched = True

        # Add user configuration
        if matched:
            view.settings().set(
                'color_helper.scan',
                {
                    "enabled": True,
                    "allow_scanning": allow_scanning,
                    "scan_scopes": scan_scopes,
                    "current_ext": ext,
                    "filters": filters,
                    "current_syntax": syntax,
                    "last_updated": ch_last_updated,
                    "output_options": outputs,
                    "color_class": colorclass,
                    "color_trigger": color_trigger
                }
            )
        else:
            # Nothing enabled here.
            view.settings().set(
                'color_helper.scan',
                {
                    "enabled": False,
                    "current_ext": ext,
                    "current_syntax": syntax,
                    "last_updated": ch_last_updated
                }
            )

        # Watch for settings changes so we can update if necessary.
        if ch_preview_thread is not None:
            if not unloading:
                view.settings().add_on_change(
                    'color_helper.reload', lambda view=view: self.on_view_settings_change(view)
                )
            ch_preview_thread.ignore_all = False

    def should_update(self, view):
        """Check if an update should be performed."""

        force_update = False
        rules = view.settings().get('color_helper.scan', None)
        if rules:
            last_updated = rules.get('last_updated', None)
            if last_updated is None or last_updated < ch_last_updated:
                force_update = True
            file_name = view.file_name()
            ext = os.path.splitext(file_name)[1].lower() if file_name is not None else None
            old_ext = rules.get('current_ext')
            if ext != old_ext:
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
                    ch_preview_thread.modified = True
                    ch_preview_thread.time = time()

    def ignore_event(self, view):
        """Check if event should be ignored."""

        return (
            view.settings().get('is_widget', False) or
            ch_preview_thread is None or
            ch_preview_thread.ignore_all or
            unloading
        )


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
    global unloading

    unloading = True
    if ch_preview_thread is not None:
        ch_preview_thread.kill()
    for w in sublime.windows():
        for v in w.views():
            v.settings().clear_on_change('color_helper.reload')
            v.settings().erase('color_helper.scan')
            v.erase_phantoms('color_helper')
    unloading = False

    if ch_settings.get('inline_previews', False):
        # ch_preview = ChPreview()
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
            v.settings().erase('color_helper.scan')
            v.erase_phantoms('color_helper')

    unloading = False
