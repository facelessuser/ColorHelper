# ColorHelper 4.0.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 4.0.0

> **BREAKING CHANGE**
> If you have defined custom colors rules and specifically reference `xyz`  
> rules should be updated to refer to `xyz` as `xyz-d65`.

- **NEW**: Update to latest `coloraide` which provides minor bug fixes.  
  As the new version now includes type annotations, ColorHelper now  
  requires the `typing` dependency until it can be migrated to use Python  
  3.8. Typing refactor did moderately affect custom color classes.
- **NEW**: `xyz` is now known as `xyz-d65` in the settings file.  
  If you have custom rules that override or add `xyz`, please update  
  the rules to reference `xyz-d65` instead.
- **NEW**: Gamut mapping now uses Oklch instead of CIE LCH per CSS recnet  
  specifications changes to the CSS Level 4 specification.
- **NEW**: Expose sRGB Linear color space per the CSS specification.
- **FIX**: Fix `blend` and `blenda` regression in emulation of Sublime's  
  ColorMod implementation.
- **FIX**: ColorPicker should not show colors maps with opacity in the  
  color map square.
