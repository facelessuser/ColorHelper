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

--8<-- "refs.md"
