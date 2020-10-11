# Configuring ColorHelper

## Overview

Settings for Color Helper are contained within the `color_helper.sublime-settings` file. There are a number of options
that control the ColorHelper experiences. This ranges from tweaking how colors are previewed, what colors are scanned
in what files, what features are enabled, etc.sublime-settings

## Multiconf

Certain settings that are likely to be useful being configured per OS or per host will be configured to use `multiconf`.
`multiconf` is a library that will parse a setting as a normal setting or a per OS and/or per host setting (if
configured properly). For the settings that have this enabled, you can optionally use the format below to specify the
setting per OS or per host.

The optional `multiconf` format requires a dictionary with a special identifier `#multiconf#`  and a list of
dictionaries identified by a qualifier of the form:

```js
    "<qualifier name>:<qualifier value>[;<qualifier name>:<qualifier value>]..."
```

For example, the following setting

```js
    "user_home": "/home"
```

would result in `get("user_home")` returning the value "/home" but it could also
be replaced with

```js
    "user_home":  {
                    "#multiconf#": [
                        {"os:windows": "C:\\Users"},
                        {"os:linux;host:his_pc": "/home"},
                        {"os:linux;host:her_pc": "/home/her/special"}
                    ]
    }
```

Now the same configuration file will provide different values depending on the machine it's on. On an MS Windows machine
the value returned by `get` will be "C:\\Users", and on a Linux machine with the host name `his_pc` the value will be
"/home", etc.

--8<-- "refs.md"
