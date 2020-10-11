# Color Picker

## `enable_color_picker`

Enables the ability to launch the color picker from the tooltip.  By default, the internal color picker will be used.

```js
    // Enable color picker option.  Will use native color picker
    // unless "use_color_picker_package" is enabled and external
    // package is installed.
    "enable_color_picker": true,
```

## `use_color_picker_package`

If you have [@weslly][weslly]'s [ColorPicker][color-picker] package installed, `user_color_picker_package` will cause
ColorHelper to use the ColorPicker package instead of the internal color picker. But only the default color picker
supports transparency.

```js
    // Use https://github.com/weslly/ColorPicker for the color picker if installed.
    "use_color_picker_package": false,
```

--8<-- "refs.md"
