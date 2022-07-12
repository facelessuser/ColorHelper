# ColorHelper 5.0.0

New release!

See `Preferences->Package Settings->ColorHelper->Changelog` for more info on  
prior releases.

Restart of Sublime Text may be required.

# 5.0.0

> **BREAKING CHANGE**: Newest `coloraide` was updated. It is approaching  
> a 1.0 release. In the path to a 1.0 release some refactoring and  
> reworking caused custom color classes to break. All internal color  
> classes should be fine, but any users that created custom local  
> color classes will need to update the color classes and color spaces  
> to work with the latest version.

- **NEW**: Upgrade to latest `coloraide`.
- **NEW**: Many new color spaces have been added and can optionally  
  be included via the new `add_to_default_spaces` option. Some that  
  were available previously are no longer registered by default.  
  See `add_to_default_spaces` in the settings file to enable more  
  spaces. A restart of Sublime Text is required when changing this  
  setting.
- **NEW**: Add new `add_to_default_spaces` which allows a user to add  
  NEW color spaces to the default color space so that the new spaces  
  can be saved and recognized in palettes and other areas of ColorHelper.  
  Modifying this setting requires a restart of Sublime Text. Custom  
  color classes should only be used to modifying previously added  
  color spaces to add to recognized input and output formats.
