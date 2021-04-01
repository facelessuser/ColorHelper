# Frequently Asked Questions

## Hex Uppercase

> How do I output hex in uppercase?

Some people prefer hex to all be in uppercase, and some may prefer lowercase. ColorHelper, by default, outputs strings
in lowercase. But worry not, as you can change this via the settings. ColorHelper 2 used to have a `upper_case_hex`
option, but ColorHelper 3 is a bit different.

In order to make ColorHelper more flexible than ever, we created a dependency called [`coloraide`][coloraide]
which is used to handle all the conversions, CSS string parsing, and CSS string output. This library allows for each
color space to define its own string output [options][coloraide-strings]. These options are exposed via the settings.

Each configuration for a given file type will specify a "color class". For instance, HTML and CSS use `css-level-4` by
default.

```js
    "color_rules": [
        {
            "name": "HTML/CSS",
            "base_scopes": [
                "source.css",
                "text.html"
            ],
            "color_class": "css-level-4", // <--- specified color class
```

If there was a desire to make make any rule that uses `css-level-4` output hex in uppercase, the color class
configuration options could be overridden in `user_color_classes`:

```js
    "user_color_classes": {
        "css-level-4": {
            "output": [
                {"space": "srgb", "format": {"hex": true, "upper": true}}, // <--- `upper` forces hex to uppercase
                {"space": "srgb", "format": {"comma": true}},
                {"space": "hsl", "format": {"comma": true}},
                {"space": "hwb", "format": {"comma": false}},
                {"space": "lch", "format": {"comma": false}},
                {"space": "lab", "format": {"comma": false}},
                {"space": "display-p3", "format": {}},
                {"space": "rec2020", "format": {}},
                {"space": "prophoto-rgb", "format": {}},
                {"space": "a98-rgb", "format": {}},
                {"space": "xyz", "format": {}}
            ]
        }
    },
```

Simply reference the name of the color class you wish to override under `user_color_classes`, specify the "key" you wish
to override (`output` in our case) and provide your new preferences. Any options that would normally be passed to
ColorAide's `to_string` function can be passed via the `format` parameter under `output`. In our case, we want to pass
in `upper` as `#!py3 True`.

--8<-- "refs.md"
