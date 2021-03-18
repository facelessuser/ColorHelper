# ColorHelper

## 3.1.4

- **FIX** Fix `tmTheme` handling of compressed hex colors.

## 3.1.3

- **FIX**: A few fixes to new style.

## 3.1.2

- **FIX**: Improved visuals for popups and `TextInputHandlers`. Improve consistency  
  in how things are presented.
- **FIX**: In color picker, values in the hue channel should clamp at 359 not 360 as  
  360 wraps to 0.
- **FIX**: Fix a few transitions between different popups.

## 3.1.1

- **FIX**: Fix Windows color picker not processing color properly.
- **FIX**: Make sure Windows color picker stores and retrieves custom colors.

## 3.1.0

- **NEW**: Drop support for ColorPicker package and instead implement OS color pickers  
  directly in ColorHelper. Linux users will need to install [`kcolorchooser`](https://apps.kde.org/en/kcolorchooser),  
  and it must be in the path on the command line

## 3.0.2

- **FIX**: Fix typo in color trigger pattern in 3.0.1 fix.

## 3.0.1

- **FIX**: Ignore color keywords when they are preceded by `$` (SCSS). Also fix issue  
  with `-` trailing a keyword.

## 3.0.0

- **NEW**: New supported color spaces: `lch`, `lab`, `display-p3`, `rec-2020`, `xyz`,  
  `prophoto-rgb`, `a98-rgb`, and `hsv`.
- **NEW**: `rgb`, `hsl`, and `hwb` all support the new CSS format `rgb(r g b / a)`.
- **NEW**: `gray()` dropped as it is no longer part of the CSS level 4 specifications.
- **NEW**: All instances of `blacklist` and `whitelist` are now known as `blocklist`  
  and `allowlist` respectively.
- **NEW**: Outputs, when inserting or converting, can be controlled in settings file.
- **NEW**: Color triggers (what ColorHelper searches for before testing if the text  
  is a color) can be configured in settings file. This can allow a user to not trigger  
  on certain formats.
- **NEW**: If desired, users can provided a custom color class object to use for certain  
  files that can augment one or more supported color space's accepted input and output  
  formats.
- **NEW**: Improvements to scanning. Scanning will only occur in the viewable viewport.  
  Text that is not visible, both vertically or horizontally, will not be scanned until  
  it scrolls into view.
- **NEW**: New option `preview_on_select` to show color previews only when the cursor is  
  on the color or selecting the color (currently only applied to one selection).
- **NEW**: New color edit tool which allows a user to get a live update of the color as  
  they alter the coordinates, and allows the user to mix it with one other color. The  
  result can be inserted back into the file, or will be handed back to the color picker  
  if called from there.
- **NEW**: New color contrast tool which allows a user to see the contrast ratio and  
  see a visual representation of how the two colors contrast. The resulting foreground  
  color can be inserted back into the file, or will be handed back to the color picker  
  if called from there.
- **NEW**: New Sublime ColorMod tool which allows a user to see a `color-mod` expression  
  update a live color preview on the fly.
- **NEW**: Only one color rule (defined in the settings file) will apply to a given view.
- **NEW**: Renamed `color_scan` option to `color_rule`.
- **NEW**: Massive overhaul of color scanning and color scanning options.
- **NEW**: Colors that are out of gamut will be gamut mapped. On hover of the preivew  
  (on ST4), it will indicate that it has been gamut mapped. This can be changed via  
  `show_out_of_gamut_preview`, and additionally a fully transparent color swatch with a  
  "red-ish" border will be shown (color may vary based on color scheme). On mouse over,  
  it will also indicate that it is out of gamut on ST4.
- **NEW**: ColorHelper will now gamut map colors in some scenarios, either due to  
  necessity, or by user setting.
- **NEW**: New `generic` option is defined which provides a default input and output for  
  files with no rules. Users can use the color picker, and other color tools, from any  
  file now. Scanning is disabled by default and can be enabled if desired. `generic` can  
  be tweaked to provide whatever fallback experience the user desired.
- **NEW**: New command added to force scanning in a file that may have scanning disabled.  
  Also can force a file with scanning enabled to be disabled.
- **NEW**: Color helper will now recognize `transparent`.
- **NEW**: Color picker rainbow box will adjust based on the saturation of the current  
  selected color.
- **NEW**: Color picker will give a clear indication when you are at the end of a color  
  channel by showing no more boxes.
- **NEW**: Provide `user_color_rules` where a user can append rules without overwriting the  
  entire rule set. If a rule uses the same `name` as one of the existing default rules,  
  a shallow merge will be done so the values of the top level keys will be overridden  
  with the user keys and/or any additional keys will be added.
- **REMOVED**: Color completion. It mainly got in the way. The palette can be called any  
  time the user needs it.
- **REMOVED**: Hex shaped color picker option has been removed.
- **REMOVED**: Removed "current file palette". ColorHelper will no longer scan the entire  
  current file and generate a palette. This only worked in a limited number of files and  
  added much more complexity.
- **REMOVED**: Various options from rules sets. These are now controlled by the color  
  class object that is being used. For instance, input and output format of colors in the  
  form `#AARRGGBB` instead of the default `#RRGGBBAA` would need to use the new example  
  `ColorHelper.custom.ahex.ColorAhex` custom color object to read in and output hex colors  
  with leading alpha channels.
- **FIX**: Insert logic issues.
- **FIX**: ColorPicker now will always work in the color space of the current mode. This  
  fixes some conversion issues.

## 2.7.1

- **FIX**: Fix issues with 2.7.X release and latest mdpopups.

## 2.7.0

- **NEW**: HSL can support alpha channels as `hsl` or `hsla` (per the CSS spec).
- **NEW**: HSL and HWB now support units `deg`, `turn`, `rad`, `grad` for the hue channel.

## 2.6.0

- **NEW**: Enable CSS level 4 colors by default.
- **NEW**: Reduce borders and in some cases remove borders around color previews.
- **NEW**: Allow insertion of colors when there is an active selection.
- **NEW**: Add option to override the border color used around color previews in  
the popup.
- **FIX**: Reduce busy processes when idle.
- **FIX**: Fixes for SCSS and Sass packages.
- **FIX**: Fix issue where inline color phantom could make the line height larger.
- **FIX**: Fix compressed hex with alpha handling.
- **FIX**: Fix `hwb` display in info dialog.
- **FIX**: Project palettes not showing up.
- **FIX**: Fix for compressed hex colors with alpha.
- **FIX**: Ensure minimum size of graphics in order to prevent issue where an  
error is thrown when image size is too small.

## 2.5.1

- **FIX**: Flicker of colors due to overly aggressive color preview deletion.
- **FIX**: Update to latest `rgba` library.

## 2.5.0

- **NEW**: Use the newer API for opening settings [#78](https://github.com/facelessuser/ColorHelper/pull/78).
- **NEW**: Require ST 3124+ (this will also be limited in Package Control soonish).
- **NEW**: Add basic support for Less [#92](https://github.com/facelessuser/ColorHelper/pull/92).
- **FIX**: Small fonts are not as small now.

## 2.4.2

- **FIX**: Fix HTML escape of palette names. [#84](https://github.com/facelessuser/ColorHelper/issues/84)
- **FIX**: Fix preview clicking. [#81](https://github.com/facelessuser/ColorHelper/issues/81)
- **FIX**: Fix margins on previews. [#83](https://github.com/facelessuser/ColorHelper/issues/83)

## 2.4.1

- **FIX**: Speed improvements for rendering previews.
- **FIX**: More fixes for duplicate preview prevention.

## 2.4.0

- **NEW**: More subtle preview borders. [7e983cd](https://github.com/facelessuser/ColorHelper/commit/7e983cda9682648eb86fc556b65578f6319f7661)
- **FIX**: Setting race condition. [2336ee5](https://github.com/facelessuser/ColorHelper/commit/2336ee554fb6add79ccd1a0ad1ac15d3c4576e39)
- **FIX**: Fix preview tagging. [#72](https://github.com/facelessuser/ColorHelper/issues/72)
- **FIX**: Fix CSS3 support. [#73](https://github.com/facelessuser/ColorHelper/issues/73)
- **FIX**: Consistent handling hex casing. [#74](https://github.com/facelessuser/ColorHelper/issues/74)

## 2.3.0

- **NEW**: New quickstart command in menu.
- **NEW**: Links in menu to navigate to official documentation and issue tracker.
- **FIX**: Fix for Sass. [#68](https://github.com/facelessuser/ColorHelper/issues/68)

## 2.2.0

- **New**: Add support for stTheme and search cdata [#59](https://github.com/facelessuser/ColorHelper/pull/59).
- **NEW**: Workaround for Windows 10 HiDpi large image issue [#61](https://github.com/facelessuser/ColorHelper/issues/61).  
See [document](http://facelessuser.github.io/ColorHelper/usage/#line_height_workaround) for more info.
- **NEW**: Added toggle support for left/right positioned previews [#65](https://github.com/facelessuser/ColorHelper/pull/65).  
See [document](http://facelessuser.github.io/ColorHelper/usage/#inline_preview_position) for more info.
- **FIX**: Web Color insertion bug [#62](https://github.com/facelessuser/ColorHelper/issues/63).
- **FIX**: Preview duplication bug (hopefully -- please report if not fixed) [#57](https://github.com/facelessuser/ColorHelper/issues/57).

## 2.1.1

- **FIX**: CSS tweaks (minihtml)
- **FIX**: Support for CSS3 package

## 2.1.0

- **NEW**: Moved popup panel formatting into external template files. Requires  
mdpopups 1.9.3.
- **FIX**: Fix issues where certain popups (colorpicker after manual color  
edit) would get overridden by auto-popups of the color info panel.
- **FIX**: Issues related to inserted colors.
- **FIX**: Fixed issue where certain colors that required word boundaries where  
still getting marked even though they were preceeded by invalid characters such  
as `@#$.-_`.

## 2.0.5

- **FIX**: Fix changelog typo
- **FIX**: Fix odd behavior when checking padding

## 2.0.4

- **NEW**: Changelog command available in `Package Settings->ColorHelper`.  
Will render a full changelog in an HTML phantom in a new view.
- **FIX**: Move colorbox before color  I like this as now the colorbox resides  
within the region of the color.  And they will all line up even if color  
format is different following them. (Fixes #46)
- **FIX**: Fix flicker on colorbox click. (Fixes #41)

## 2.0.3

- **FIX**: Don't allow previews to truncated colors.
- **FIX**: When validating existing phantoms, ensure the scopes still match  
(like when code gets commented out etc.).
- **FIX**: Support new rem units if using mdpopups 1.8.0 for better font  
scaling.

## 2.0.2

- **FIX**: Fix breakage for ST versions without phantoms.

## 2.0.1

- **FIX**: Less clearing of inline images.
- **FIX**: Per os/host setting for inline_preview_offset and graphic_size.
- **FIX**: Single border around preview that contrasts with the the theme  
background.

## 2.0.0

- **NEW**: Show inline color previews in Sublime Text 3118+! Can be turned off  
if the feature is not desired.
- **NEW**: *Should* update mdpopups to the latest one on Package Control  
upgrade (restart required after upgrade).  Haven't actually confirmed if it  
works.
- **FIX**: Images should scale with font size in Sublime Text 3118+. You can  
still select small, medium, and large resources, but they will be relative to  
the font size now.

## 1.4.2

- **FIX**: #39 Fix font size too small in popup.

## 1.4.1

- **FIX**: Remove distortion workarounds as later Sublime versions no longer  
distort images.
- **FIX**: Utilize latest mdpopups to handle font sizes.

## 1.4.0

- **NEW**: Allow disabling status message via the settings file option  
`show_status_index`.
- **FIX**: Fix decimal level tracking when indexing.

## 1.3.5

- **FIX**: Fixed issue where stored decimal size was faulty and could cause  
the current file color indexing to fail.

## 1.3.4

- **FIX**: Fix logic for populating a view's ColorHelper specific settings on  
activation and save.

## 1.3.3

- **FIX**: Fixes related to gray, hsla, and hwba.

## 1.3.2

- **FIX**: Fix version in message.

## 1.3.1

- **FIX** Forgot to strip extension on syntax compare.

## 1.3.0

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

## 1.2.1

- **FIX**: Remove project commands that do nothing

## 1.2.0

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

## 1.1.0

- **NEW**: Color picker built into the tooltips (optionally can be overridden  
with ColorPicker Package's color picker).
- **NEW**: Graphic sizes are now configurable in settings.
- **NEW**: Color tooltip used to popup up when a user started to type a color,  
but would stay open even when the user ignored it. Now it will auto close in  
this scenario.
- **NEW**: Settings are accessible via `Preferences->Package Settings->ColorHelper`  
in the menu. Support for the SCSS package added.

## 1.0.3

- **FIX**: Use dependency that does not clash
- **FIX**: Add more scope support for POST CSS

## 1.0.2

- **FIX**: Typo in code where view_window should have been view.window

# ColorHlper 1.0.1

- **FIX**: Markdown dependency needs to not clash with default Markdown  
package. Renamed to python-markdown.

## 1.0.0

- **NEW**: Initial release.
