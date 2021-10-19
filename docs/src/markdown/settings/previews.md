# Previews

## `inline_previews`

Enable/disable inline color previews. `inline_previews` generates an image previews after the identified color in your
source file.  You can click the preview to bring up the ColorHelper panel.

## `inline_preview_position`

Previews can be positioned to the left or right of a color. Set this value to "left" or "right to toggle its behavior.

```js
    // Adjust the position of inline image previews.
    // (left|right)
    "inline_preview_position": "left",
```

## `preview_on_select`

Enables/disables previews only showing when they are selected.

```js
    // Only show color previews next to a color when the color region
    // intersects the current selection(s). If a selection is empty
    // (just a caret), if the caret is at the start or within the color
    // region, a preview will also show.
    "preview_on_select": false ,
```

## `show_out_of_gamut_preview`

Controls whether previews will attempt to gamut map a color that is out of the preview gamut.

```js
    // Controls whether previews will try to visually show an out of gamut
    // color by using gamut mapping.
    "show_out_of_gamut_preview": true,
```

## `gamut_space`

!!! warning "Experimental Feature"

!!! new "New in 3.8.0"

Select the gamut space used for color previews. You should only pick a space that matches your system. If you happen
to have a display that does not align with one of the spaces below, you may just have to pick whatever is closest.

Preview accuracy is based on how precise Sublime is able to render colors and how close one of these profiles aligns
to your display and it's currently configured profile. If at one time, Sublime actually manages colors, this may or may
not be required, or may change in functionality. If your display supports Display P3, but is configured with a profile
for sRGB, then you should not touch the below setting.

```js
    // The gamut space to render previews in.
    // Supported spaces are: `srgb`, `display-p3`, `rec2020`,
    //                       `a98-rgb`, and `prophoto-rgb`.
    // If your display does not run with one of these gamuts,
    // You should not change this.
    "gamut_space": "srgb",
```

--8<-- "refs.md"
