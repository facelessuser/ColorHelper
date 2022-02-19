# ColorHelper 4.2.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on  
prior releases.

Restart of Sublime Text may be required.

- **NEW**: Upgrade `coloraide` library which brings back color mapping  
  mapping in CIELCH. While interpolation is great in Oklab/Oklch, gamut  
  mapping with chroma reduction in Oklch has some less desirable corner  
  cases. Using Oklch is in the early stages in the CSS Color Level 4 spec  
  and there needs to be more time for this mature and be tested more.
- **NEW**: `oklab()` and `oklch()` CSS format is now available. This form  
  is based on the published CSS Level 4 spec and requires lightness to be  
  a percentage. In the future, it is likely that percentages will be  
  optional for lightness and could even be applied to some of the other  
  components, but currently, such changes are in some early drafts and  
  not currently included in ColorHelper.
