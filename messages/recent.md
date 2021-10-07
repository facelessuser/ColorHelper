# ColorHelper 3.7.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 3.7.0

- **NEW**: Color Picker for HWB is not enabled by default anymore, but can  
  be enabled if desired via settings.
- **NEW**: ColorPicker improvements. Can now configure which color pickers  
  are enabled. Can specify a preferred color picker. Can specify whether  
  ColorHelper should take a color space and auto load the matching color  
  picker if it is enabled. Add new HSV, Okhsl, and Okhsv color pickers.
- **NEW**: New `coloraide` dependency may break custom color spaces not  
  provided with ColorHelper. If having issues, please open an issue to  
  get help. It is doubtful that many have delved too deeply in this area.
- **FIX**: Better behavior of color picker's handling of color.
- **FIX**: Fix issues with [Advanced Substation Alpha (ASS)](https://packagecontrol.io/packages/Advanced%20Substation%20Alpha%20(ASS))
  support.
- **FIX**: Remove unnecessary dependencies.
- **FIX**: Upgrade `coloraide` which brings the possibility of using CIELuv,  
  LCH~uv~, DIN99o, DIN99o LCH, Okhsl, and Okhsv. Small improvements and fixes  
  also included.
