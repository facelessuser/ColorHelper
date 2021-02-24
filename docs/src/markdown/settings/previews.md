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
    // intersects the current selection. Currently only supported with
    // single selections. If selection is empty (just a caret),
    // If the caret is at the start or within the color region, a preview
    // will also show.
    "preview_on_select": false ,
```

## `show_out_of_gamut_preview`

Controls whether previews will attempt to gamut map a color that is out of the preview gamut.

```js
    // Controls whether previews will try to visually show an out of gamut
    // color by using gamut mapping.
    "show_out_of_gamut_preview": true,
```

--8<-- "refs.md"
