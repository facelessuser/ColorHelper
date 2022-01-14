# ColorHelper 4.1.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on
prior releases.

Restart of Sublime Text may be required.

## 4.1.0

- **NEW**: Add minimal color support in Sublime's built-in GraphViz  
  syntax files. Colors are currently limited to hex RGB/RGBA and color  
  names outside of HTML and full CSS support inside HTML. Support is  
  experimental, and if false positives are a problem, the rule can be  
  disabled in the settings.
- **NEW**: Don't default `tmtheme` custom class output to X11 names,  
  default to hex codes instead.
- **FIX**: Fix some additional custom class issues related to latest  
  `coloraide` update.
