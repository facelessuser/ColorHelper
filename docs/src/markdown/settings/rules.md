# Configuring ColorHelper

## `color_rules`

The `color_rules` option configures how ColorHelper interacts with a given file. In order for ColorHelper to inject
color previews, translate colors, and various other tasks it needs context, and rules provide that context.

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

!!! tip
    New rules and rule overrides should be added to [`user_color_rules`](#user_color_rules) instead of modifying
    `color_rules` directly.

### `name`

Optional name. If a user creates a rule in `user_color_rules`, and it it shares the same `name` as a rule under 
`color_rules`, a shallow merge of the two rules will be made which will allow the user rule to override the values
of top level keys.

```js
    "name": "HTML/CSS",
```

### `sytnax_files`

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

- `scopes`: A string that defines a base scope that the color class applies to.

- `class`:  The name of the color class profile to use (defined in [`color_classes`](#color_classes)).

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
"(?i)(?:\b(?<![-#&])(?:color|hsla?|gray|lch|lab|hwb|rgba?)\(|\b(?<![-#&])[\w]{3,}(?!\()\b|(?<![&])#)"
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
colors. By default, these color classes accept inputs that match valid CSS. They also output colors in the form of valid
CSS.

It may be desirable to filter out certain color spaces, or even alter a color space to accept different input formats
and generate different output formats. This can all be done by subclassing the `Color` class.

`color_classes` allows you to configure the `Color` class, or point to a custom `Color` class and configure it.

`color_classes` is a dictionary of color profiles that link to a specific `Color` class. You can tweak options
specifically related to the `Color` class. The **key** is the name of the color profile  which can be referenced by
[`color_rules`](#color_rules). The **value** is a dictionary of options.

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

This allows a user to specify a custom color class derived from `coloraide.Color`. This could be used to reference
a custom color class that can recognize different formats when scanning for colors. A custom color class will often also
provide different string outputs and string output options.

The value should be the full import path for the `Color` class.

ColorHelper provides a few custom color classes in `ColorHelper.custom`. You can check out those to see how to create
your own.

```js
"class": "ColorHelper.custom.tmtheme.ColorSRGBX11",
```

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
