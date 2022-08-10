"""
ColorHelper.

Copyright (c) 2015 - 2017 Isaac Muse <isaacmuse@gmail.com>
License: MIT
"""
import sublime
import sublime_plugin
import threading
from time import time, sleep
import re
import os
import mdpopups
from .lib import colorbox
from . import ch_util as util
import traceback
from .lib.multiconf import get as qualify_settings
from collections import namedtuple

PREVIEW_IMG = (
    '<style>'
    'html, body {{margin: 0; padding: 0;}} a {{line-height: 0;}}'
    '</style>'
    '<a href="{}"{}>{}</a>'
)

PREVIEW_BORDER_SIZE = 1

reload_flag = False
ch_last_updated = None
ch_settings = None
unloading = False

if 'ch_preview_thread' not in globals():
    ch_preview_thread = None


def preview_is_on_left():
    """Return boolean for positioning preview on left/right."""
    return ch_settings.get('inline_preview_position') != 'right'


class ColorSwatch(namedtuple('ColorSwatch', ['start', 'end', 'pid', 'uid'])):
    """Color swatch."""


class Extent(namedtuple('Extent', ['start', 'end'])):
    """Range of dimension."""


class Dimensions(namedtuple('Dimensions', ['x', 'y'])):
    """Dimensions."""


class ColorHelperPreviewOverrideCommand(sublime_plugin.TextCommand):
    """Override current scanning state."""

    def run(self, edit):
        """Override the current scan "allow" state for this specific view."""

        override = self.view.settings().get("color_helper.scan_override", "Remove override")
        if override == "Force enable":
            self.options = ["Force disable", "Remove override"]
        elif override == "Force disable":
            self.options = ["Force enable", "Remove override"]
        else:
            self.options = ["Force enable", "Force disable"]

        self.view.window().show_quick_panel(self.options, self.done)

    def done(self, value):
        """Check the selection."""

        if value != -1:
            option = self.options[value]
            self.view.settings().set("color_helper.scan_override", option)
            if option == "Force enable":
                self.view.settings().set("color_helper.scan_override", option)
                ch_preview_thread.modified = True
                ch_preview_thread.time = time()
            elif option == "Force disable":
                self.view.settings().set("color_helper.scan_override", option)
                self.view.window().run_command("color_helper_preview", {"clear": True})
            else:
                self.view.settings().erase("color_helper.scan_override")
                self.view.window().run_command("color_helper_preview", {"clear": True})


class ColorHelperPreviewCommand(sublime_plugin.WindowCommand):
    """Color Helper preview with phantoms."""

    def __init__(self, window):
        """Setup."""

        super().__init__(window)
        self.previous_region = {}
        self.previews = {}
        self.color_classes = {}
        for view in window.views():
            view.erase_phantoms("color_helper")

    def on_navigate(self, href):
        """Handle color box click."""

        self.view.sel().clear()
        for k, v in self.previews[self.view.buffer_id()].items():
            if href == v.uid:
                phantom = self.view.query_phantom(v.pid)
                if phantom:
                    self.view.sel().add(sublime.Region(int(v.end), int(v.start)))
                    sublime.set_timeout(
                        lambda cmd="color_helper", args={"mode": "info"}: self.view.run_command(cmd, args),
                        100
                    )
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

    def is_selected(self, region, sels):
        """Check if region is in selections."""

        for s in sels:
            if region.intersects(s) or s.a == region.a:
                return True
        return False

    def get_selections(self, bounds):
        """Get selections that intersect viewport."""

        selections = []
        for s in self.view.sel():
            b = Dimensions(*self.view.text_to_layout(s.b))
            if b.y <= bounds.y.start:
                # We are pass the viewport
                continue
            a = Dimensions(*self.view.text_to_layout(s.a))
            if a.y >= bounds.y.end:
                # We haven't reached the view port yet
                break
            if (
                (bounds.x.start <= a.x <= bounds.x.end or bounds.x.start <= b.x <= bounds.x.end) or
                not (
                    (a.x >= bounds.x.end and b.x >= a.x and a.y == b.y) or
                    (b.x <= bounds.x.start and a.x <= b.x and a.y == b.y) or
                    (a.x >= bounds.x.end and b.x <= bounds.x.start and a.y + 1 == b.y)
                )
            ):
                selections.append(s)
        return selections

    def source_iter(self, visible_region, bounds):
        """
        Iterate through source in the viewport.

        We don't want to provide all the content in a really wide scrollable view,
        so clip each line in the visible region to the visible viewport.

        Return content in consecutive chunks.
        """

        # Get all the lines
        lines = self.view.split_by_newlines(visible_region)

        # Calculate regions of consecutive lines that do not have gaps due to clipping
        last_start = None
        last_end = None
        for line in lines:
            # Line start
            start_clipped = False
            start_vector = Dimensions(*self.view.text_to_layout(line.begin()))
            if start_vector.x < bounds.x.start:
                start_pt = self.view.layout_to_text((bounds.x.start, start_vector.y))
                if start_pt == line.begin():
                    if last_start is not None:
                        yield sublime.Region(last_start, last_end)
                        last_start = None
                        last_end = None
                        continue
                start_clipped = True
            else:
                start_pt = line.begin()

            # Line end
            end_clipped = False
            end_vector = Dimensions(*self.view.text_to_layout(line.end()))
            if end_vector.x > bounds.x.end:
                end_pt = self.view.layout_to_text((bounds.x.end, end_vector.y))
                end_clipped = True
            else:
                end_pt = line.end()

            # This region should not be included with the last
            # as there is a gap between the last content and this content.
            if start_clipped and last_start is not None:
                yield sublime.Region(last_start, last_end)
                last_start = None
                last_end = None

            # This content has been clipped and will have a gap between
            # this and the next region, so just send it now.
            if end_clipped:
                yield sublime.Region(last_start if last_start is not None else start_pt, end_pt)
                last_start = None
                last_end = None
                continue

            # Track this region to see if we can include more in one chunk
            # If we already have a start, just update the end.
            if last_start is None:
                last_start = start_pt
            last_end = end_pt

        # Return anything we haven't already
        if last_start is not None:
            yield sublime.Region(last_start, last_end)

    def get_color_class(self, pt, classes):
        """Get color class based on selection scope."""

        view_id = self.view.buffer_id()
        if not self.color_classes[view_id] or self.view.settings().get('color_helper.refresh', True):
            util.debug("Clear color class stash")
            self.view.settings().set('color_helper.refresh', False)
            self.color_classes[view_id] = util.get_settings_colors()

        # Check if the first point within the color matches our scope rules
        # and load up the appropriate color class
        color_class = None
        filters = []
        for item in classes:
            try:
                value = self.view.score_selector(pt, item["scopes"])
                if not value:
                    continue
                else:
                    class_options = self.color_classes[view_id].get(item["class"])
                    if class_options is None:
                        continue
                    module = class_options.get("class", "ColorHelper.lib.coloraide.Color")
                    if isinstance(module, str):
                        if module == "ColorHelper.lib.coloraide.Color":
                            color_class = self.base
                        else:
                            # Initialize the color module and cache it for this view
                            color_class = util.import_color(module)
                        class_options["class"] = color_class
                    else:
                        color_class = module
                    filters = class_options.get("filters", [])
                    break
            except Exception:
                pass
        return color_class, filters

    def setup_gamut_options(self):
        """Setup gamut options."""

        self.show_out_of_gamut_preview = ch_settings.get('show_out_of_gamut_preview', True)
        self.gamut_space = ch_settings.get('gamut_space', 'srgb')
        if self.gamut_space not in util.GAMUT_SPACES:
            self.gamut_space = 'srgb'
        self.out_of_gamut = self.base("transparent").convert(self.gamut_space)
        self.out_of_gamut_border = self.base(self.view.style().get('redish', "red")).convert(self.gamut_space)

    def do_search(self, force=False):
        """
        Perform the search for the highlighted word.

        TODO: This function is a big boy. We should look into breaking it up.
              With that said, this is low priority.
        """

        # Since the plugin has been reloaded, force update.
        global reload_flag
        settings = self.view.settings()
        colors = []

        view_id = self.view.buffer_id()

        # Allow per view scan override
        option = settings.get("color_helper.scan_override", None)
        if option in ("Force enable", "Force disable"):
            override = option == "Force enable"
        else:
            override = None

        # Get the rules and use them to get the needed scopes.
        # The scopes will be used to get the searchable regions.
        rules = util.get_rules(self.view)
        # Bail if this if this view has no valid rule or scanning is disabled.
        if (
            rules is None or not rules.get("enabled", False) or
            (not rules.get("allow_scanning", True) and not override) or
            override is False
        ):
            self.erase_phantoms()
            return

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
        old_box_height = int(settings.get('color_helper.box_height', 0))
        current_color_scheme = settings.get('color_scheme')
        if (
            force or old_box_height != box_height or
            current_color_scheme != settings.get('color_helper.color_scheme', '') or
            settings.get('color_helper.refresh')
        ):
            self.erase_phantoms()
            settings.set('color_helper.color_scheme', current_color_scheme)
            settings.set('color_helper.box_height', box_height)
            force = True

        # Get viewable bounds so we can constrain both vertically and horizontally.
        visible_region = self.view.visible_region()
        position = self.view.viewport_position()
        dimensions = self.view.viewport_extent()
        bounds = Dimensions(
            Extent(position[0], position[0] + dimensions[0] - 1),
            Extent(position[1], position[1] + dimensions[1] - 1)
        )

        # If we don't need to force previews,
        # quit if visible region is the same as last time
        if not force and self.previous_region[view_id] == bounds:
            return
        self.previous_region[view_id] = bounds

        # Setup "preview on select"
        preview_on_select = ch_settings.get("preview_on_select", False)
        show_preview = True
        sels = []
        if preview_on_select:
            show_preview = False
            sels = self.get_selections(bounds)
            if sels:
                show_preview = True

        # Get the scan scopes
        scanning = rules.get("scanning")
        classes = rules.get("color_class", "css-level-4")
        if show_preview and visible_region.size() and scanning and classes:
            # Get out of gamut related options
            self.setup_gamut_options()

            # Get triggers that identify where colors are likely
            color_trigger = re.compile(rules.get("color_trigger", util.RE_COLOR_START))

            # Find source content in the visible region.
            # We will return consecutive content, but if the lines are too wide
            # horizontally, they will be clipped and returned as separate chunks.
            for src_region in self.source_iter(visible_region, bounds):
                source = self.view.substr(src_region)
                start = 0

                # Find colors in this source chunk.
                for m in color_trigger.finditer(source):
                    # Test if we have found a valid color
                    start = m.start()
                    src_start = src_region.begin() + start

                    # Check if the first point within the color matches our scope rules
                    # and load up the appropriate color class
                    color_class, filters = self.get_color_class(src_start, classes)
                    if color_class is None:
                        continue

                    # Check if scope matches for scanning
                    try:
                        value = self.view.score_selector(src_start, scanning)
                        if not value:
                            continue
                    except Exception:
                        continue

                    obj = color_class.match(source, start=start)
                    if obj is not None and obj.color.space() not in filters:
                        obj = None
                    if obj is not None:
                        # Calculate true start and end of the color source
                        src_end = src_region.begin() + obj.end
                        region = sublime.Region(src_start, src_end)

                        # If "preview on select" is enabled, only show preview if within a selection
                        # or if the selection as no width and the color comes right after.
                        if preview_on_select and not self.is_selected(region, sels):
                            continue
                    else:
                        continue

                    # Calculate point at which we which to insert preview
                    position_on_left = preview_is_on_left()
                    pt = src_start if position_on_left else src_end
                    if str(region.begin()) in self.previews[view_id]:
                        # Already exists
                        continue

                    # Calculate a reasonable border color for our image at this location and get color strings
                    hsl = self.base(
                        mdpopups.scope2style(self.view, self.view.scope_name(pt))['background']
                    ).convert("hsl")
                    hsl['lightness'] = hsl['lightness'] + (0.3 if hsl.luminance() < 0.5 else -0.3)
                    preview_border = hsl.convert(self.gamut_space, fit=True).set('alpha', 1)

                    color = self.base(obj.color)
                    title = ''
                    if self.gamut_space == 'srgb':
                        check_space = self.gamut_space if color.space() not in util.SRGB_SPACES else color.space()
                    else:
                        check_space = self.gamut_space
                    if not color.in_gamut(check_space):
                        title = ' title="Preview out of gamut"'
                        if self.show_out_of_gamut_preview:
                            pcolor = color.convert(self.gamut_space, fit=True)
                            preview1 = pcolor.clone().set('alpha', 1)
                            preview2 = pcolor
                        else:
                            preview1 = self.out_of_gamut
                            preview2 = self.out_of_gamut
                            preview_border = self.out_of_gamut_border
                    else:
                        pcolor = color.convert(self.gamut_space, fit=True)
                        preview1 = pcolor.clone().set('alpha', 1)
                        preview2 = pcolor

                    # Create preview
                    unique_id = str(time()) + str(region)
                    html = PREVIEW_IMG.format(
                        unique_id,
                        title,
                        colorbox.color_box(
                            [preview1, preview2], preview_border,
                            height=box_height, width=box_height,
                            border_size=PREVIEW_BORDER_SIZE, check_size=check_size,
                            gamut_space=self.gamut_space
                        )
                    )
                    colors.append(
                        (
                            html,
                            pt,
                            region.begin(),
                            region.end(),
                            unique_id
                        )
                    )

            # Add all previews
            self.add_phantoms(colors)

            # The phantoms may have altered the viewable region,
            # so set previous region to the current viewable region
            visible_region = self.view.visible_region()
            position = self.view.viewport_position()
            dimensions = self.view.viewport_extent()
            bounds = Dimensions(
                Extent(position[0], position[0] + dimensions[0] - 1),
                Extent(position[1], position[1] + dimensions[1] - 1)
            )
            self.previous_region[view_id] = bounds

    def add_phantoms(self, colors):
        """Add phantoms."""

        i = self.view.buffer_id()
        for html, pt, start, end, unique_id in colors:
            pid = self.view.add_phantom(
                'color_helper',
                sublime.Region(pt),
                html,
                0,
                on_navigate=self.on_navigate
            )
            self.previews[i][str(start)] = ColorSwatch(start, end, pid, unique_id)

    def reset_previous(self):
        """Reset previous region."""
        self.previous_region[self.view.buffer_id()] = sublime.Region(0)

    def erase_phantoms(self):
        """Erase phantoms."""

        # Obliterate!
        self.view.erase_phantoms('color_helper')
        self.previews[self.view.buffer_id()].clear()
        self.reset_previous()

    def run(self, clear=False, force=False):
        """Run."""

        self.base = util.get_base_color()
        self.view = self.window.active_view()
        ids = set([view.buffer_id() for view in self.window.views()])
        keys = set(self.previews.keys())
        diff = keys - ids

        for i in diff:
            del self.previews[i]
            del self.previous_region[i]
            del self.color_classes[i]

        i = self.view.buffer_id()
        if i not in self.previews:
            self.previews[i] = {}
        if i not in self.previous_region:
            self.previous_region[i] = sublime.Region(0, 0)
        if i not in self.color_classes:
            self.color_classes[i] = {}

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
        self.scroll_wait_time = 0.5
        self.sleep = 0.25
        self.time = time()
        self.modified = False
        self.ignore_all = False
        self.abort = False
        self.scroll = False
        self.last_view = -1
        self.scroll_view = None

    def scroll_check(self):
        """Check if we should issue a scroll event."""

        view = sublime.active_window().active_view()
        if view is None:
            return
        vid = view.id()
        this_scroll = vid
        if self.last_view != this_scroll:
            self.last_view = this_scroll
            self.scroll = True
        else:
            scroll_view = view.viewport_position(), view.viewport_extent()
            if scroll_view != self.scroll_view:
                self.scroll = True
                self.scroll_view = scroll_view
                self.time = time()

    def payload(self):
        """Code to run."""

        view = sublime.active_window().active_view()
        if view is None:
            return

        if not self.ignore_all:
            clear = False
            force = False
            if self.modified:
                force = True
                self.modified = False
                self.scroll = False
            else:
                self.scroll = False

            # Ignore selection and edit events inside the routine
            try:
                args = {"clear": clear, "force": force}
                window = view.window()
                if window is not None:
                    window.run_command('color_helper_preview', args)
            except Exception:
                util.debug(str(traceback.format_exc()))

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
                delta = time() - self.time
                if delta > self.wait_time and (self.modified is True or self.scroll is True):
                    sublime.set_timeout_async(self.payload, 0)
                elif delta > self.scroll_wait_time:
                    sublime.set_timeout_async(self.scroll_check, 0)
            sleep(self.sleep)


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
            ch_preview_thread.modified = True

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
        view.window().run_command("color_helper_preview", {"clear": True})

        file_name = view.file_name()
        ext = os.path.splitext(file_name)[1].lower() if file_name is not None else None
        s = sublime.load_settings('color_helper.sublime-settings')
        rules = util.get_settings_rules()
        syntax = os.path.splitext(view.settings().get('syntax').replace('Packages/', '', 1))[0]

        # Check if view meets criteria for on of our rule sets
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
            scanning = ','.join(rule.get("scanning", []))
            classes = rule.get("color_class", "css-level-4")
            if isinstance(classes, str):
                classes = [{"class": classes, "scopes": ""}]
            allow_scanning = bool(rule.get("allow_scanning", True) and scanning)
            color_trigger = rule.get("color_trigger", util.RE_COLOR_START)
            matched = True
            break

        # Couldn't find any explicit options, so associate a generic  option set to allow basic functionality..
        if not matched:
            generic = s.get("generic", {})
            scanning = ",".join(generic.get("scanning", []))
            classes = generic.get("color_class", "css-level-4")
            if not isinstance(classes, str):
                classes = []
            else:
                classes = [{"class": classes, "scopes": ""}]
            allow_scanning = bool(generic.get("allow_scanning", True) and scanning)
            color_trigger = generic.get("color_trigger", util.RE_COLOR_START)
            matched = True

        # Add user configuration
        if matched:
            view.settings().set(
                'color_helper.scan',
                {
                    "enabled": True,
                    "allow_scanning": allow_scanning,
                    "scanning": scanning,
                    "current_ext": ext,
                    "current_syntax": syntax,
                    "last_updated": ch_last_updated,
                    "color_trigger": color_trigger,
                    "color_class": classes
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
            v.settings().erase('color_helper.scan_override')
            v.settings().set('color_helper.refresh', True)
            v.erase_phantoms('color_helper')
    unloading = False

    if ch_settings.get('inline_previews', False):
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
            v.settings().erase('color_helper.scan_override')
            v.erase_phantoms('color_helper')

    unloading = False
