"""Development tools for color helper."""
import sublime
import sublime_plugin
from . import color_helper_util as util
import sys
import traceback

PY38 = (3, 8) <= sys.version_info

if PY38:
    from importlib import reload as imp_reload
else:
    from imp import reload as imp_reload


class ColorHelperReloadColorClassCommand(sublime_plugin.ApplicationCommand):
    """Force a reload of custom color class modules."""

    def run(self):
        """Run command."""

        color_classes = util.get_settings_colors()

        for k, v in color_classes.items():
            color_class = v.get("class", "coloraide.Color")
            # Don't reload the built-in module.
            if not color_class.startswith('coloraide.'):
                module = color_class.rsplit('.', 1)[0]
                if module in sys.modules:
                    try:
                        sys.modules[module] = imp_reload(sys.modules[module])
                        util.log("Reloaded '{}'".format(module))
                    except Exception:
                        util.log(str(traceback.format_exc()))
        # Ensure all windows refresh their cache of color classes
        for window in sublime.windows():
            for view in window.views():
                view.settings().set('color_helper.refresh', True)

    def is_enabled(self, **kwargs):
        """Check if enabled."""

        return sublime.load_settings('color_helper.sublime-settings').get("debug", False)
