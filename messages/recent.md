# ColorHelper 3.3.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 3.3.0

- **NEW**: `preview_on_select` now supports multi-select.
- **NEW**: Color picker channels only show 10 steps back or forward at a given
  time instead of 12 and are always perfectly scaled between 0% - 100%.
- **NEW**: Color box now shows hue on x-axis and saturation on y-axis. It also
  replaces the gray scale bar with a lightness bar.
- **NEW**: Color picker now is more compact and hides the sliders unless the
  user switches to slider mode. In that case, the color box will be hidden.
- **NEW**: Only the color picker's alpha channel will show a representation of
  transparency. This allows the user to clearly see the color when adjusting
  other channels.
- **NEW**: Color box in the color picker now shows an approximate indicator of
  where the current color falls on the color box.
- **NEW**: Add indication of which button is selected in the color picker.
- **NEW**: Vendor `coloraide` as ColorHelper is tightly coupled to it. Vendoring
  will ensure a better upgrade process. The default color classe is now referenced
  via `ColorHelper.lib.coloraide` opposed to the old `coloraide`.
- **FIX**: Fix issues related to detecting when colors are in the visible viewport.
- **FIX**: Ensure that when a native color picker is called with no color, that if
  the default color is picked, it will insert instead of ignore.

## Updated from 2.0 to 3.0?

ColorHelper 3.0 is a major overhaul, so existing settings are likely to break.
Please checkout the latest documentation to learn what changed and how to
configure and use the new ColorHelper: https://facelessuser.github.io/ColorHelper/.

You may need to run `Package Control: Satisfy Dependencies`, wait until it finishes
in the console, and then restart Sublime before the latest ColorHelper works.
