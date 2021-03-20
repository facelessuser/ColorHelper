# ColorHelper 3.1.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
the release.

## Overview 3.1.0

- A lot of style overhaul. An attempt to display the information in a more
  consistent manner.
- Image scaling is more consistent. "Medium" should now be 1:1 with the
  current view's scaling of images. "Small" and "large" will scale the images
  to be smaller or larger relative to medium. You can always use `graphic_scale`
  and set scaling to an arbitrary scaling opposed to the preset sizes in
  `graphic_size`.
- Some issues dealing with storing "favorite" colors has been resolved. All palettes
  used to be stored differently than they were compared. This caused a saved
  favorite to appear not saved in the info panel. But they were in the palette.
- The new Windows native color picker did not run properly in ST4. This issue has
  been resolved.
- Other minor usability improvements.

## Updated from 2.0 to 3.0?

ColorHelper 3.0 is a major overhaul, so existing settings are likely to break.
Please checkout the latest documentation to learn what changed and how to
configure and use the new ColorHelper: https://facelessuser.github.io/ColorHelper/.

You may need to run `Package Control: Satisfy Dependencies`, wait until it finishes
in the console, and then restart Sublime before the latest ColorHelper works.
