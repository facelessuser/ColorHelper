# Color Picker

## `enable_color_picker`

Enables the ability to launch the color picker from the tooltip.  By default, the internal color picker will be used.

```js
    // Enable color picker option.  Will use native color picker
    // unless "use_color_picker_package" is enabled and external
    // package is installed.
    "enable_color_picker": true,
```

## `use_os_color_picker`

If you wish to use your native color picker available with your OS, you can set this option to `#!py3 True`. This will
use the native color picker on macOS and Windows. If on Linux, and you have [`kcolorchooser`][kcolorchooser]
installed (KDE not required) and in your command line path, then it will be used.

```js
    // Use native, OS specific color pickers. Linux requires `kcolorchooser`.
    "use_os_color_picker": false,
```

## `enabled_color_picker_modes`

By default color pickers are available in the sRGB, HSL, and HSV color space. sRGB actually just uses the HSL color
space picker with sRGB sliders.

In addition to the default color pickers, one can enable HWB (HSL color picker with HWB sliders), Okhsl, Okhsv, and
HSLuv which are alternatives to the HSL and HSV color spaces. Okhsl and Okhsl are derived from Oklab, and HSLuv is
derived from CIE Luv.

```js
    // Enable the preferred color picker options: `srgb`, `hsl`, `hsv`, `hwb`, `okhsl`, `okhsv`, `hsluv`
    // If no valid spaces are specified, `srgb` will be used.
    "enabled_color_picker_modes": ["srgb", "hsl", "hsv"],
```

## `auto_color_picker_mode`

Controls whether ColorHelper, based on the input color, decides which color space to use. If a matching color space
cannot be found, the preferred color space picker will be selected.

```js
    // If the color is already in the space of an enabled mode, use that mode.
    // If disabled, the "preferred" mode will be used.
    "auto_color_picker_mode": true,
```

## `preferred_color_picker_mode`

The preferred color picker space to use. If invalid or not enabled, the first enabled color space will be used, and if
there are none enabled, `srgb` will be used as a last resort.

```js
    // If "auto" mode is disabled, or the "auto" mode could not determine a suitable picker,
    // the preferrreed color picker space will be used. If the preferred is invalid, the
    // first picker from `enabled_color_picker_modes` will be used, and if that is not valid,
    // `srgb` will be used.
    "preferred_color_picker_mode": "hsl",
```

--8<-- "refs.md"
