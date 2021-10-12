# ColorHelper 3.7.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 3.7.0

- **NEW**: Color contrast tool will now take any color space, even non-sRGB,  
  but the tool will only operate in the sRGB gamut as the compositing of  
  transparent colors defaults to sRGB and the contrast targeting algorithm  
  is currently done in the sRGB gamut using HWB. It will more clearly show  
  that the color has been gamut mapped in the results as it will now show  
  the modified color at all times.
- **NEW**: Upgrade `coloraide` which brings the possibility of using CIELuv,  
  LCH~uv~, DIN99o, DIN99o LCH, Okhsl, and Okhsv. Small improvements and fixes  
  also included.
- **NEW**: `color(xyz x y z)` now references D65 XYZ per latest CSS  
  specifications. `color(xyz-d50 x y z)` is now the old D50 XYZ variant.  
  `color(xyz-d65 x y z)` is also an alias for `color(xyz x y z)`.
- **NEW**: HSV and HSL store non-hue channels internally in the range of  
  0 - 1 instead of 0 - 100. This affects the `color(space)` output form.
- **NEW**: Color Picker for HWB is not enabled by default anymore, but can  
  be enabled if desired via settings.
- **NEW**: ColorPicker improvements. Can now configure which color pickers  
  are enabled. Can specify a preferred color picker. Can specify whether  
  ColorHelper should take a color space and auto load the matching color  
  picker if it is enabled. Add new HSV, Okhsl, and Okhsv color pickers.
- **NEW**: New `coloraide` dependency may break custom color spaces not  
  provided with ColorHelper. If having issues, please open an issue to  
  get help. It is doubtful that many have delved too deeply in this area.
- **FIX**: Fix typos and wording in various color tool dialogs.
- **FIX**: Better behavior of color picker's handling of color.
- **FIX**: Fix issues with [Advanced Substation Alpha (ASS)](https://packagecontrol.io/packages/Advanced%20Substation%20Alpha%20(ASS))
  support.
- **FIX**: Remove unnecessary dependencies.
