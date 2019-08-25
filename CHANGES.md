# ColorHelper 2.6.0

- **NEW**: Enable CSS level 4 colors by default.
- **NEW**: Reduce borders and in some cases remove borders around color previews.
- **NEW**: Allow insertion of colors when there is an active selection.
- **NEW**: Add option to override the border color used around color previews in the popup.
- **FIX**: Reduce busy processes when idle.
- **FIX**: Fixes for SCSS and Sass packages.
- **FIX**: Fix issue where inline color phantom could make the line height larger.
- **FIX**: Fix compressed hex with alpha handling.
- **FIX**: Fix `hwb` display in info dialog.
- **FIX**: Project palettes not showing up.
- **FIX**: Fix for compressed hex colors with alpha.
- **FIX**: Ensure minimum size of graphics in order to prevent issue where an error is thrown when image size is too small.

# ColorHelper 2.5.1

- **FIX**: Flicker of colors due to overly aggressive color preview deletion.
- **FIX**: Update to latest `rgba` library.

# ColorHelper 2.5.0

- **NEW**: Use the newer API for opening settings [#78](https://github.com/facelessuser/ColorHelper/pull/78).
- **NEW**: Require ST 3124+ (this will also be limited in Package Control soonish).
- **NEW**: Add basic support for Less [#92](https://github.com/facelessuser/ColorHelper/pull/92).
- **FIX**: Small fonts are not as small now.

# ColorHelper 2.4.2

- **FIX**: Fix HTML escape of palette names. [#84](https://github.com/facelessuser/ColorHelper/issues/84)
- **FIX**: Fix preview clicking. [#81](https://github.com/facelessuser/ColorHelper/issues/81)
- **FIX**: Fix margins on previews. [#83](https://github.com/facelessuser/ColorHelper/issues/83)

# ColorHelper 2.4.1

- **FIX**: Speed improvements for rendering previews.
- **FIX**: More fixes for duplicate preview prevention.

# ColorHelper 2.4.0

- **NEW**: More subtle preview borders. [7e983cd](https://github.com/facelessuser/ColorHelper/commit/7e983cda9682648eb86fc556b65578f6319f7661)
- **FIX**: Setting race condition. [2336ee5](https://github.com/facelessuser/ColorHelper/commit/2336ee554fb6add79ccd1a0ad1ac15d3c4576e39)
- **FIX**: Fix preview tagging. [#72](https://github.com/facelessuser/ColorHelper/issues/72)
- **FIX**: Fix CSS3 support. [#73](https://github.com/facelessuser/ColorHelper/issues/73)
- **FIX**: Consistent handling hex casing. [#74](https://github.com/facelessuser/ColorHelper/issues/74)

# ColorHelper 2.3.0

- **NEW**: New quickstart command in menu.
- **NEW**: Links in menu to navigate to official documentation and issue tracker.
- **FIX**: Fix for Sass. [#68](https://github.com/facelessuser/ColorHelper/issues/68)

# ColorHelper 2.2.0

- **New**: Add support for stTheme and search cdata [#59](https://github.com/facelessuser/ColorHelper/pull/59).
- **NEW**: Workaround for Windows 10 HiDpi large image issue [#61](https://github.com/facelessuser/ColorHelper/issues/61).  
See [document](http://facelessuser.github.io/ColorHelper/usage/#line_height_workaround) for more info.
- **NEW**: Added toggle support for left/right positioned previews [#65](https://github.com/facelessuser/ColorHelper/pull/65).  
See [document](http://facelessuser.github.io/ColorHelper/usage/#inline_preview_position) for more info.
- **FIX**: Web Color insertion bug [#62](https://github.com/facelessuser/ColorHelper/issues/63).
- **FIX**: Preview duplication bug (hopefully -- please report if not fixed) [#57](https://github.com/facelessuser/ColorHelper/issues/57).

# ColorHelper 2.1.1

- **FIX**: CSS tweaks (minihtml)
- **FIX**: Support for CSS3 package

# ColorHelper 2.1.0

- **NEW**: Moved popup panel formatting into external template files. Requires  
mdpopups 1.9.3.
- **FIX**: Fix issues where certain popups (colorpicker after manual color  
edit) would get overridden by auto-popups of the color info panel.
- **FIX**: Issues related to inserted colors.
- **FIX**: Fixed issue where certain colors that required word boundaries where  
still getting marked even though they were preceeded by invalid characters such  
as `@#$.-_`.

# ColorHelper 2.0.5

- **FIX**: Fix changelog typo
- **FIX**: Fix odd behavior when checking padding

# ColorHelper 2.0.4

- **NEW**: Changelog command available in `Package Settings->ColorHelper`.  
Will render a full changelog in an HTML phantom in a new view.
- **FIX**: Move colorbox before color  I like this as now the colorbox resides  
within the region of the color.  And they will all line up even if color  
format is different following them. (Fixes #46)
- **FIX**: Fix flicker on colorbox click. (Fixes #41)

# ColorHelper 2.0.3

- **FIX**: Don't allow previews to truncated colors.
- **FIX**: When validating existing phantoms, ensure the scopes still match  
(like when code gets commented out etc.).
- **FIX**: Support new rem units if using mdpopups 1.8.0 for better font  
scaling.

# ColorHelper 2.0.2

- **FIX**: Fix breakage for ST versions without phantoms.

# ColorHelper 2.0.1

- **FIX**: Less clearing of inline images.
- **FIX**: Per os/host setting for inline_preview_offset and graphic_size.
- **FIX**: Single border around preview that contrasts with the the theme  
background.

# ColorHelper 2.0.0

- **NEW**: Show inline color previews in Sublime Text 3118+! Can be turned off  
if the feature is not desired.
- **NEW**: *Should* update mdpopups to the latest one on Package Control  
upgrade (restart required after upgrade).  Haven't actually confirmed if it  
works.
- **FIX**: Images should scale with font size in Sublime Text 3118+. You can  
still select small, medium, and large resources, but they will be relative to  
the font size now.

# ColorHelper 1.4.2

- **FIX**: #39 Fix font size too small in popup.

# ColorHelper 1.4.1

- **FIX**: Remove distortion workarounds as later Sublime versions no longer  
distort images.
- **FIX**: Utilize latest mdpopups to handle font sizes.

# ColorHelper 1.4.0

- **NEW**: Allow disabling status message via the settings file option  
`show_status_index`.
- **FIX**: Fix decimal level tracking when indexing.

# ColorHelper 1.3.5

- **FIX**: Fixed issue where stored decimal size was faulty and could cause  
the current file color indexing to fail.

# ColorHelper 1.3.4

- **FIX**: Fix logic for populating a view's ColorHelper specific settings on  
activation and save.

# ColorHelper 1.3.3

- **FIX**: Fixes related to gray, hsla, and hwba.

# ColorHelper 1.3.2

- **FIX**: Fix version in message.

# ColorHelper 1.3.1

- **FIX** Forgot to strip extension on syntax compare.

# ColorHelper 1.3.0

- **NEW**: Color preview will now show transparent colors with and without  
transparency.
- **NEW**: Transparent colors can now be stored and showed in palettes.
- **NEW**: Specifying files for scanning has been reworked and is now more  
flexible.
- **NEW**: Color Helper no longer has preferred formats when inserting. It  
will always prompt the user for their desired input format.
- **NEW**: Added CSS4's rebeccapurple to the webcolor names.
- **NEW**: Added better rgb and rgba support: percentage format, decimal  
format (CSS4), percentage alpha (CSS4).
- **NEW**: Added support for alpha channel as percentage for hsla (CSS4).
- **NEW**: Support CSS4 gray, hwb, and hex values with alpha channels.
- **NEW**: Option to read hex with alpha channel as `#AARRGGBB` instead of  
`#RRGGBBAA`.
- **NEW**: Option to compress hex values if possible on output: `#334455` -->  
`#345`.
- **NEW**: Can disable auto-popups if desired.
- **NEW**: Insert options now are now more dynamic and only show valid options  
for the current view.
- **FIX**: Clamp color channel values out of range.

# ColorHelper 1.2.1

- **FIX**: Remove project commands that do nothing

# ColorHelper 1.2.0

- **NEW**: Color picker will appear in palette panel if no color info panel  
is allowed.
- **NEW**: Added "supported_syntax_incomplete_only" for incomplete colors that  
may not yet be scoped within a valid scope due to being incomplete.
- **NEW**: In the color picker, instead of the select link, you now must  
choose the css format to insert via the corresponding `>>>` link.
- **NEW**: Add alternate rectangular color picker look. You can use the new  
form by disabling the hex color picker look via the use_hex_color_picker  
setting.
- **NEW**: Added new CSS Color Name picker (available in the color picker).
- **FIX**: When manually forcing the popup via the command palette, the
tooltip was getting closed. ColorHelper is now aware of manual and auto popup  
tooltips and will only auto close the auto popups when ignored while typing.

# ColorHelper 1.1.0

- **NEW**: Color picker built into the tooltips (optionally can be overridden  
with ColorPicker Package's color picker).
- **NEW**: Graphic sizes are now configurable in settings.
- **NEW**: Color tooltip used to popup up when a user started to type a color,  
but would stay open even when the user ignored it. Now it will auto close in  
this scenario.
- **NEW**: Settings are accessible via `Preferences->Package Settings->ColorHelper`  
in the menu. Support for the SCSS package added.

# ColorHelper 1.0.3

- **FIX**: Use dependency that does not clash
- **FIX**: Add more scope support for POST CSS

# ColorHelper 1.0.2

- **FIX**: Typo in code where view_window should have been view.window

# ColorHlper 1.0.1

- **FIX**: Markdown dependency needs to not clash with default Markdown  
package. Renamed to python-markdown.

# ColorHelper 1.0.0

- **NEW**: Initial release.
