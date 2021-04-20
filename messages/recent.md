# ColorHelper 3.3.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 3.4.0

- **NEW**: Fix typo. `0xahex` color class should have been named `0xhex` in the  
  settings.
- **NEW**: New `coloraide` brings support for `oklab`, `oklch`, `jzazbz`, `jzczhz`,  
  `ICtCp`, D65 variations of CIELAB, CIELCH, and XYZ (none of which are enabled  
  by default).
- **NEW**: Some refactoring of `coloraide` caused custom color classes to get  
  updated. User created custom classes may have to get updated to work.
- **FIX**: Upgrade `coloraide` which fixes issues related to inconsistent use of  
  D65 white values in XYZ transforms and Bradford CAT and other lesser bug fixes  
  as well. This particularly improves conversions to and from CIELAB.

## Updated from 2.0 to 3.0?

ColorHelper 3.0 is a major overhaul, so existing settings are likely to break.
Please checkout the latest documentation to learn what changed and how to
configure and use the new ColorHelper: https://facelessuser.github.io/ColorHelper/.

You may need to run `Package Control: Satisfy Dependencies`, wait until it finishes
in the console, and then restart Sublime before the latest ColorHelper works.
