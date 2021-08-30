# ColorHelper 3.5.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 3.5.0

- **NEW**: `generic` rule will now allow scanning in strings by default. If this  
  is not desired, simply modify it in user settings to reflect desired behavior.
- **NEW**: Remove default palette file as it just contained examples that most  
  people would never use.
- **NEW**: Color palettes now provide a format version so that they can be upgraded  
  if needed. Due to the compatibility issue with a change for `color()` format,  
  color palettes will be upgraded.
- **FIX**: `color()` format for `lab` and other colors that have percentage only  
  channels must require those channels to be input as percentages per the CSS  
  level 4 specifications. This affects the string output for the `color()` format  
  as well.
- **FIX**: Latest `coloraide` improves gamut mapping.
- **FIX**: Small gamut fitting adjustments.
- **FIX**: Fix issue with duplicate previews when working with clone views.

## Updated from 2.0 to 3.0?

ColorHelper 3.0 is a major overhaul, so existing settings are likely to break.
Please checkout the latest documentation to learn what changed and how to
configure and use the new ColorHelper: https://facelessuser.github.io/ColorHelper/.

You may need to run `Package Control: Satisfy Dependencies`, wait until it finishes
in the console, and then restart Sublime before the latest ColorHelper works.
