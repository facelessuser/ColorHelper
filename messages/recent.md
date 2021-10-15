# ColorHelper 3.7.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 3.8.0

- **NEW**: Allow selecting the preview gamut to control what RGB space  
  images previews are rendered in. For instance, before this change,  
  macOS computers with Display P3 monitors would render sRGB colors  
  as Display P3 colors and could provide inaccurate previews. Now  
  you can set `gamut_space` to `display-p3` and sRGB and Display P3  
  colors will be closer to their actual color. Gamut can be set to  
  `srgb`, `display-p3`, `a98-rgb`, `prophoto-rgb`, and `rec2020`.  
  Colors will on only make sense on displays of these types.
