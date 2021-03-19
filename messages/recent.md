# ColorHelper 3.1.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
the release.

## Overview 3.1.0

- A lot of style overhaul. An attempt to display the information in a more
  consistent manner.
- Generally the font will always match your current view's font size. Images
  scale with the font size. Depending on your monitor size and resolution,
  sometimes, images can sometimes be too small with small font sizes or too
  big if you use a very large font size. "Medium" should now be 1:1 with the
  current view's scaling of images. "Small" and "large" will scale the images
  to be smaller or larger relative to medium. You can always use `graphic_scale`
  and set scaling to an arbitrary scaling opposed to the preset sizes in
  `graphic_size`.
- Some issues dealing with storing favorites colors has been resolved. All palettes
  used to be stored in high precision, but often the colors are inserted and rounded
  to smaller precision. Now, colors will be stored in pallets with the default precision
  which is also used when inserting colors back into a file. This should ensure that
  ColorHelper can detect if a given color is stored in favorites or not.
- The new Windows native color picker did not run properly in ST4. This issue has
  been resolved.
- Other minor usability improvements.

## Updated from 2.0 to 3.0?

ColorHelper 3.0 is a major overhaul, so existing settings are likely to break.
Please checkout the latest documentation to learn what changed and how to
configure and use the new ColorHelper: https://facelessuser.github.io/ColorHelper/.

You may need to run `Package Control: Satisfy Dependencies`, wait until it finishes
in the console, and then restart Sublime before the latest ColorHelper works.
