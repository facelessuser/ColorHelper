# ColorHelper

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on  
prior releases.

A restart of Sublime Text is **strongly** encouraged.

Please report any issues as we _might_ have missed some required updates  
related to the upgrade to stable `coloraide`.

## 6.2.0

- **NEW**: Since browsers do not and may not introduce Color Level 4  
  gamut mapping until some future spec, make gamut mapping approach  
  configurable. Use clipping by default to match browsers as this is  
  likely what people expect even if it is not an ideal approach. Use  
  `gamut_map` in settings option to manually control the approach.
- **NEW**: Upgrade ColorAide to 2.4.
- **FIX**: Fix regression where contrast logic could not adjust to a  
  given contrast due to a property access.
