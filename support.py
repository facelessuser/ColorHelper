"""Support command."""
import sublime
import sublime_plugin
import textwrap
import webbrowser
import re

__version__ = "6.3.1"
__pc_name__ = 'ColorHelper'

CSS = '''
div.color-helper { padding: 10px; margin: 0; }
.color-helper h1, .color-helper h2, .color-helper h3,
.color-helper h4, .color-helper h5, .color-helper h6 {
    {{'.string'|css}}
}
.color-helper blockquote { {{'.comment'|css}} }
.color-helper a { text-decoration: none; }
'''


def list2string(obj):
    """Convert list to string."""

    return '.'.join([str(x) for x in obj])


def format_version(module, attr, call=False):
    """Format the version."""

    try:
        if call:
            version = getattr(module, attr)()
        else:
            version = getattr(module, attr)
    except Exception as e:
        print(e)
        version = 'Version could not be acquired!'

    if not isinstance(version, str):
        version = list2string(version)
    return version


def is_installed_by_package_control():
    """Check if installed by package control."""

    settings = sublime.load_settings('Package Control.sublime-settings')
    return str(__pc_name__ in set(settings.get('installed_packages', [])))


class ColorHelperSupportInfoCommand(sublime_plugin.ApplicationCommand):
    """Support info."""

    def run(self):
        """Run command."""

        info = {}

        info["platform"] = sublime.platform()
        info["version"] = sublime.version()
        info["arch"] = sublime.arch()
        info["plugin_version"] = __version__
        info["pc_install"] = is_installed_by_package_control()
        try:
            import mdpopups
            info["mdpopups_version"] = format_version(mdpopups, 'version', call=True)
        except Exception:
            info["mdpopups_version"] = 'Version could not be acquired!'

        msg = textwrap.dedent(
            """\
            - ST ver.: %(version)s
            - Platform: %(platform)s
            - Arch: %(arch)s
            - Plugin ver.: %(plugin_version)s
            - Install via PC: %(pc_install)s
            - mdpopups ver.: %(mdpopups_version)s
            """ % info
        )

        sublime.message_dialog(msg + '\nInfo has been copied to the clipboard.')
        sublime.set_clipboard(msg)


class ColorHelperOpenSiteCommand(sublime_plugin.ApplicationCommand):
    """Open site links."""

    def run(self, url):
        """Open the URL."""

        webbrowser.open_new_tab(url)


class ColorHelperDocCommand(sublime_plugin.WindowCommand):
    """Open doc page."""

    re_pkgs = re.compile(r'^Packages')

    def on_navigate(self, href):
        """Handle links."""

        if href.startswith('sub://Packages'):
            sublime.run_command('open_file', {"file": self.re_pkgs.sub('${packages}', href[6:])})
        else:
            webbrowser.open_new_tab(href)

    def run(self, page):
        """Open page."""

        try:
            import mdpopups
            has_phantom_support = (mdpopups.version() >= (1, 10, 0)) and (int(sublime.version()) >= 3124)
        except Exception:
            has_phantom_support = False

        if not has_phantom_support:
            sublime.run_command('open_file', {"file": page})
        else:
            text = sublime.load_resource(page.replace('${packages}', 'Packages'))
            view = self.window.new_file()
            view.set_name('ColorHelper - Quick Start')
            view.settings().set('gutter', False)
            view.settings().set('word_wrap', False)
            if has_phantom_support:
                mdpopups.add_phantom(
                    view,
                    'quickstart',
                    sublime.Region(0),
                    text,
                    sublime.LAYOUT_INLINE,
                    css=CSS,
                    wrapper_class="color-helper",
                    on_navigate=self.on_navigate
                )
            else:
                view.run_command('insert', {"characters": text})
            view.set_read_only(True)
            view.set_scratch(True)


class ColorHelperChangesCommand(sublime_plugin.WindowCommand):
    """Changelog command."""

    def run(self):
        """Show the changelog in a new view."""
        try:
            import mdpopups
            has_phantom_support = (mdpopups.version() >= (1, 10, 0)) and (int(sublime.version()) >= 3124)
        except Exception:
            has_phantom_support = False

        text = sublime.load_resource('Packages/ColorHelper/CHANGES.md')
        view = self.window.new_file()
        view.set_name('ColorHelper - Changelog')
        view.settings().set('gutter', False)
        view.settings().set('word_wrap', False)
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
