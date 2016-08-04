"""Changelog."""
import sublime
import sublime_plugin

CSS = '''
.color-helper h1, .color-helper h2, .color-helper h3, .color-helper h4, .color-helper h5, .color-helper h6 {
    {{'.string'|css('color')}}
}
.color-helper blockquote { {{'.comment'|css('color')}} }

.color-helper {
  {{'.background'|css('background-color')}}
  {{'.foreground'|css('color')}} }
  padding: 0;
  margin: 0;
}
'''


class ColorHelperChangesCommand(sublime_plugin.WindowCommand):
    """Changelog command."""

    def run(self):
        """Show the changelog in a new view."""
        import mdpopups

        text = sublime.load_resource('Packages/ColorHelper/CHANGES.md')
        view = self.window.new_file()
        view.set_name('ColorHelper - Changelog')
        view.settings().set('gutter', False)
        mdpopups.add_phantom(
            view,
            'changelog',
            sublime.Region(0),
            text,
            sublime.LAYOUT_INLINE,
            wrapper_class="color-helper",
            css=CSS
        )
        view.set_read_only(True)
        view.set_scratch(True)

    def is_enabled(self):
        """Check if is enabled."""
        try:
            import mdpopups
        except Exception:
            return False

        return (mdpopups.version() >= (1, 7, 3)) and (int(sublime.version()) >= 3118)

    is_visible = is_enabled
