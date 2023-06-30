# Configuring ColorHelper

## `add_to_default_spaces`

ColorHelper uses the `coloraide` library to provide support for all the different color spaces. `coloraide` ships with
a lot of color spaces, but only registers a select few in order to properly support CSS and a couple specific features.
ColorHelper provides a way to register additional color spaces that ship with `coloraide` (or even custom color spaces
written by a user) via the `add_to_default_spaces`.

By default, ColorHelper does enable a few additional spaces, but a user can more if they have a need. It should be noted
that a restart of Sublime Text is required for these changes to take affect as changes to this setting affect the plugin
throughout.

```js
    // This option requires a restart of Sublime Text.
    // This allows a user to add NEW previously unincluded color spaces.
    // This ensures that the new color space will work in palettes etc.
    // Then, custom color classes can override the space for special, file
    // specific formatting via the `class` attribute under `user_color_classes`.
    "add_to_default_spaces": [
        // "ColorHelper.lib.coloraide.spaces.cmy.CMY",
        // "ColorHelper.lib.coloraide.spaces.cmyk.CMYK",
        // "ColorHelper.lib.coloraide.spaces.din99o.Din99o",
        // "ColorHelper.lib.coloraide.spaces.hsi.HSI",
        // "ColorHelper.lib.coloraide.spaces.hunter_lab.HunterLab",
        // "ColorHelper.lib.coloraide.spaces.ictcp.ICtCp",
        // "ColorHelper.lib.coloraide.spaces.igtgpg.IgTgPg",
        // "ColorHelper.lib.coloraide.spaces.itp.ITP",
        // "ColorHelper.lib.coloraide.spaces.jzazbz.Jzazbz",
        // "ColorHelper.lib.coloraide.spaces.jzczhz.JzCzhz",
        // "ColorHelper.lib.coloraide.spaces.lch99o.lch99o",
        // "ColorHelper.lib.coloraide.spaces.orgb.ORGB",
        // "ColorHelper.lib.coloraide.spaces.prismatic.Prismatic",
        // "ColorHelper.lib.coloraide.spaces.rec2100pq.Rec2100PQ",
        // "ColorHelper.lib.coloraide.spaces.rlab.RLAB",
        // "ColorHelper.lib.coloraide.spaces.ucs.UCS",
        // "ColorHelper.lib.coloraide.spaces.uvw.UVW",
        // "ColorHelper.lib.coloraide.spaces.xyy.XyY",
        "ColorHelper.lib.coloraide.spaces.hsluv.HSLuv",
        "ColorHelper.lib.coloraide.spaces.lchuv.Lchuv",
        "ColorHelper.lib.coloraide.spaces.luv.Luv",
        "ColorHelper.lib.coloraide.spaces.okhsl.Okhsl",
        "ColorHelper.lib.coloraide.spaces.okhsv.Okhsv"
    ],
```

## `color_rules`

The `color_rules` option configures how ColorHelper interacts with a given file. In order for ColorHelper to inject
color previews, translate colors, and various other tasks, it needs context, and rules provide that context.

```js
    "color_rules": [
        {
            "name": "HTML/CSS",
            "base_scopes": [
                "source.css",
                "text.html"
            ],
            "color_class": "css-level-4",
            "scanning": [
                // https://packagecontrol.io/packages/CSS3
                "meta.declaration-list.css -support.type.property-name.css -comment -string",
                // CSS, CSS in HTML etc. (based on: Sublime Default)
                "meta.property-value.css -comment -string",
                // CSS3, CSS3 in HTML etc. (based on: https://packagecontrol.io/packages/CSS3)
                "meta.value.css -comment -string",
                // HTML attributes (based on: Sublime Default)
                "meta.tag.inline.any.html string.quoted -constant.character.entity.html",
                "meta.tag.any.html meta.attribute-with-value.style.html"
            ]
        }
    ]
```

A rule will define what kind of colors ColorHelper should look for, and where in the file valid colors are found.

`color_rules` is a list of rule sets, where each rule is a dictionary of options. Only one rule set can apply to a
given view at a time.

/// tip
New rules and rule overrides should be added to [`user_color_rules`](#user_color_rules) instead of modifying
`color_rules` directly.
///

### `name`

Optional name. If a user creates a rule in `user_color_rules`, and it it shares the same `name` as a rule under
`color_rules`, a shallow merge of the two rules will be made which will allow the user rule to override the values
of top level keys.

```js
    "name": "HTML/CSS",
```

### `syntax_files`

Target a view using a syntax file from the given list. Defaults to an empty list.

When specifying syntax files, you would use full path relative to `Packages`. The extension should be omitted.

```js
    "syntax_files": [
        "PackageDev/Package/Sublime Text Color Scheme/Sublime Text Color Scheme",
        "PackageDev/Package/Sublime Text Theme/Sublime Text Theme"
    ],
```

### `syntax_filter`

Specify whether [`syntax_files`](#syntax_files) is an `allowlist` or `blocklist`.  Default's to `allowlist`.

```js
    "syntax_filter": "allowlist",
```

### `base_scopes`

Target a view whose base scope matches something from the list of scopes. Defaults to an empty list.

```js
    "base_scopes": [
        "source.css",
        "text.html"
    ],
```

### `extensions`

Target a view with an extension from the provided list. Defaults to an empty list.

```js
    "extensions": [".tmTheme"],
```

### `color_class`

A string defining the name of a color class to use for the scopes within the current view. Color class name should be
defined in [`color_classes`](#color_classes).

```js
    "color_class": "css-level-4",
```

If needed, you can define multiple color classes with a list of dictionaries. Each dictionary in the list should
contain a `class` and `scopes`:

-   `scopes`: A string that defines a base scope that the color class applies to.

-   `class`:  The name of the color class profile to use (defined in [`color_classes`](#color_classes)).

```js
    "color_class": [
        {"class": "css-level-4", "scopes": "-comment -string"},
        // etc.
    ]
```

### `scanning`

Scanning will only find colors within certain scopes in a file. This is to help avoid generating previews in areas of
a document that are undesirable. Often used to avoid generating previews in comments etc.

This option is a list containing scopes that should be scanned for colors.

```js
    "scanning": true,
```

### `color_trigger`

It is slow to iterate an entire buffer directly with the color class to match colors, so do a quick search for tokens
that should trigger a color check. That way we only test in places where we think we might have a valid color. For
instance, the color class can translate colors in the form `rgb(1 1 1 / 1)`, so we can specify `rgb(` as a color
trigger. If we find `rgb(`, we will test that spot's scope and attempt to read in a color at that location. Defaults to:

```js
"(?i)(?:\b(?<![-#&])(?:color|hsla?|lch|lab|hwb|rgba?)\(|\b(?<![-#&])[\w]{3,}(?!\()\b|(?<![&])#)"
```

```js
"color_trigger": "(?i)(?:\\b(?<![-#&])[\\w]{3,}(?!\\()\\b|(?!<&)\\#)",
```

### `allow_scanning`

This is an easy way to disable just scanning within a certain rule set. Defaults to `true`.

```js
"allow_scanning": true,
```

### `enable`

This can be used to disable a color rule set entirely. Defaults to `true`.

```js
"enable": true,
```

## `user_color_rules`

Follows the same format as `color_rules`, but is made so users can append to existing color rules. If a `name` is
specified, and it matches a rule `name` in the default `color_rules`, the top level key values in the user rule will
override the values in the default rules.

```js
    // User rules. These will be appended to the normal `color_rules` unless they
    // share the same name. In that case, a shallow merge will be performed allowing
    // the values of top level keys to be overridden and new keys to be added.
    "user_color_rules": [],
```

## `generic`

This defines a generic fallback rule for files that don't match anything in `color_rules`. This allows color tools to
work anywhere by providing them with sane defaults. By default, scanning is not enabled in files with generic rules,
but you can enable it if you wish.

Generally, `generic` accepts all rules that can be applied to `color_rules` except rules that filter out specific
views such as: `sytnax_files`, `syntax_filter`, `base_scopes`, and `extensions`. Additionally, `color_class` only
accepts a string defining a single color class. It will not accept multiple color classes.

```js
    "generic": {
        "allow_scanning": false,
        "scanning": ["-comment -string"],
        "color_class": "css-level-4"
    },
```

## `color_classes`

ColorHelper uses the `Color` class from the [`coloraide`][coloraide] dependency to manage, manipulate, and translate
colors. By default, this color class contains color spaces that accept inputs that match valid CSS. They also output
colors in the form of valid CSS.

For some file types, it may be desirable to filter out certain color spaces, alter the default output options, or even
alter the input and output formats entirely.

`color_classes` is a dictionary of color profiles that link to a specific `Color` class and provides various options
you can tweak related to the `Color` class.

The **key** of the dictionary is the name of the color profile  which can be referenced by
[`color_rules`](#color_rules). The **value** is a dictionary of options.

Generally, either the base color space should be used (`ColorHelper.lib.coloraide.Color`) or one of the available
[custom color classes](https://github.com/facelessuser/ColorHelper/tree/master/custom). If none of these are sufficient,
it is possible to create your own custom class.

### `output`

This can be used to specify the output options available when converting a color or inserting a color from the color
picker or other tools. Specify the color `space` from the `Color` class to use, and the options to supply to the `Color`
class' `to_string` method. Defaults to:

```js
[
    {"space": "srgb", "format": {"hex": True}},
    {"space": "srgb", "format": {"comma": True, "precision": 3}},
    {"space": "hsl", "format": {"comma": True, "precision": 3}},
    {"space": "hwb", "format": {"comma": False, "precision": 3}},
    {"space": "lch", "format": {"comma": False, "precision": 3}},
    {"space": "lab", "format": {"comma": False, "precision": 3}},
    {"space": "xyz", "format": {}}
]
```

To learn more about available options, see [`coloraide`'s documentation][coloraide-strings].

### `class`

This allows a user to specify a custom color class derived from the default color class.

The default color class is `ColorHelper.lib.coloraide.Color`. ColorHelper also provides some additional custom classes
which are found [here](https://github.com/facelessuser/ColorHelper/tree/master/custom).

The value should be the full import path for the `Color` class.

```js
"class": "ColorHelper.custom.tmtheme.ColorSRGBX11",
```

If none of the provided color classes are sufficient, it is possible to create your own custom class. With that said,
there are a few things to note:

-   Custom classes should be derived from the default base class, but there is a catch, ColorHelper handles the default
    (`ColorHelper.lib.coloraide.Color`) special. This allows us to enable the users with the ability of defining what
    color spaces the default class contains via the [`add_to_default_spaces`](#add_to_default_spaces) setting. In turn,
    ensures all color spaces properly function in features like palettes, etc.

    So, if creating a custom color space, the user should call `ColorHelper.ch_util.get_base_color()` to get the actual
    default class to derive from. Users should **not** derive directly from `ColorHelper.lib.coloraide.Color`.

-   Colors are passed back and forth between custom color classes and the default color class. As long as both classes
    know how to handle the color space, things should work without issue.

    If a custom color class is using a color space that is not registered under the default class or is using a color
    space derived from an unregistered color space, some features won't work.

    In short, it is import to ensure that all color spaces that are actively used in custom color classes are
    registered via [`add_to_default_spaces`](#add_to_default_spaces).

    If you are creating a brand new color space, you must also register it, or a version of that color space, with the
    default color class. The registered color space must support the `color(id ...)` input and output format as that
    format is often used when passing a color around internally within ColorAide.

### `filters`

A list that restricts color recognition to only the specified color spaces. Default is an empty list which allows all
color spaces.

Allowed color spaces are `srgb`, `hsl`, `hwb`, `hsv`, `lch`, `lab`, `xyz`, `display-p3`, `rec2020`, `a98-rgb`, and
`prophoto-rgb`.

```js
"filters": ["srgb", "hsl"],
```

### `edit_mode`

Optional parameter that controls the "edit" tool that is used in the info panel when you click the large color preview.
The default value is `default`, but can also be be set to `st-colormod` to use an edit mode that mimics Sublimes
`color-mod` implementation.

This was mainly added so users could specify `st-colormod` when using a compatible color profile for color schemes and
themes.

```js
"edit_mode": "st-colormod",
```

## `user_color_classes`

Follows the same format as `color_classes`, but is made so users can append to existing color classes. If a `name` is
specified, and it matches a entry's `name` in the default `color_classes`, the top level key values in the user color
class will override the values in the default color class.

```js
    // User color classes. These will be added to the normal `color_classes` unless they
    // share the same name with an existing entry. In that case, a shallow merge will be performed allowing
    // the values of top level keys to be overridden and new keys to be added.
    "user_color_classes": {}
```

--8<-- "refs.md"
