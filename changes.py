"""Changelog."""
import sublime
import sublime_plugin
import webbrowser

CSS = '''
html { {{'.background'|css}} }
div.color-helper { padding: 0; margin: 0; {{'.background'|css}} }
.color-helper h1, .color-helper h2, .color-helper h3,
.color-helper h4, .color-helper h5, .color-helper h6 {
    {{'.string'|css}}
}
.color-helper blockquote { {{'.comment'|css}} }
.color-helper a { text-decoration: none; }
'''


class ColorHelperChangesCommand(sublime_plugin.WindowCommand):
    """Changelog command."""

    def run(self):
        """Show the changelog in a new view."""
        try:
            import mdpopups
            has_phantom_support = (mdpopups.version() >= (1, 10, 0)) and (int(sublime.version()) >= 3118)
        except Exception:
            has_phantom_support = False

        text = sublime.load_resource('Packages/ColorHelper/CHANGES.md')
        view = self.window.new_file()
        view.set_name('ColorHelper - Changelog')
        view.settings().set('gutter', False)
        if has_phantom_support:
            mdpopups.add_phantom(
                view,
                'changelog',
                sublime.Region(0),
                text,
                sublime.LAYOUT_INLINE,
                wrapper_class="color-helper",
                css=CSS,
                on_navigate=self.on_navigate
            )
        else:
            view.run_command('insert', {"characters": text})
        view.set_read_only(True)
        view.set_scratch(True)

    def on_navigate(self, href):
        """Open links."""
        webbrowser.open_new_tab(href)
