# Graphic Rendering

<!--     // If the color picker is too big or too small, try playing with this.
    // This is a coarse control which scales image size relative to the
    // approximate line height. small (1x), medium (1.5x), and large (2x).
    // (small | medium | large)
    "graphic_size": "medium",

    // Fine scaling of image sizes. Overrides `graphic_size`.
    // Use an integer or floating point value. `null` disables fine scaling.
    "graphic_scale": null,

    // For Windows 10 HiDpi setups. This is a temporary workaround
    // to help reduce abnormally large color previews and other images.
    // This will be removed once the issue is fixed in Sublime Text 3.
    "line_height_workaround": false,

    // Adjust the size of inline image previews by the offset given.
    // Please use either a positive or negative number.
    "inline_preview_offset": 0,

    // Override image border color. This is mainly for schemes that use a dramatically different
    // background for popups vs code background. Color should be either an sRGB, HSL, HWB, or named CSS color.
    "image_border_color": null, -->


## `graphic_size`

Coarse scaling of generated graphics sizes. Graphics in the tooltips look best large as Sublime slightly distorts
images, but on different screens, some of the tooltips (especially the internal color picker) may be too large or too
small. `graphic_size` can be used to control the size of these generated images.  Scaling is based off line height, and
valid settings are `small` (1X), `medium` (1.5X), and `large` (2X). `medium` is the default.

```js
    // If the color picker is too big or too small, try playing with this.
    // This is a coarse control which scales image size relative to the
    // approximate line height. small (1x), medium (1.5x), and large (2x).
    // (small | medium | large)
    "graphic_size": "medium",
```

If you need to set this per OS or per host, you can via [`multiconf`](./index.md#multiconf).

## `graphic_scale`

Fine scaling of the size of generated graphics. This overrides `graphic_size`.

```js
    // Fine scaling of image sizes. Overrides `graphic_size`.
    // Use an integer or floating point value. `null` disables fine scaling.
    "graphic_scale": 1.5,
````

If you need to set this per OS or per host, you can via [`multiconf`](./index.md#multiconf).

## `line_height_workaround`

Temporary workaround for Windows 10 HiDPI setups that reduces image sizes.

```js
    // For Windows 10 HiDPI setups.  This is a temporary workaround
    // to help reduce abnormally large color previews and other images.
    // This will be removed once the issue is fixed in Sublime Text 3.
    "line_height_workaround": false,
```

## `inline_preview_offset`

ColorHelper does its best to calculate the correct size for inline images, but with some font's or screen resolutions
(or for a reason I don't quite understand) it will get it wrong and create an image larger (or maybe smaller) than your
line height which may cause an undesirable look. Set this value to either a positive or negative value which will be
applied to the inline preview's image size.

```js
    // Adjust the size of inline image previews by the offset given.
    // Please use either a positive or negative number.
    "inline_preview_offset": 0,
```

If you need to set this per OS or per host, you can via [`multiconf`](#multiconf).

## `image_border_color`

For themes with popups that have a very different background than what is found as the default code background, it may
be desirable to override image borders with a color that blends better.

Colors specified in the setting can be of the of any valid CSS color in the sRGB, HSL, or HWB color space. `null` can be
used to remove your override.

```js
    // Override image border color. This is mainly for schemes that use a dramatically different
    // background for popups vs code background. Color should be in the form `#RRGGBB`. Alpha channels will
    // be ignored.
    "image_border_color": "rgb(0 0 0)"
```

--8<-- "refs.md"
