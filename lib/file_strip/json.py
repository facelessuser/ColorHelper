"""
File Strip
Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
"""

import re
from .comments import Comments

JSON_PATTERN = re.compile(
    r"""
        (
            (?P<square_comma>
                ,                        # trailing comma
                (?P<square_ws>[\s\r\n]*) # white space
                (?P<square_bracket>\])   # bracket
            )
          | (?P<curly_comma>
                ,                        # trailing comma
                (?P<curly_ws>[\s\r\n]*)  # white space
                (?P<curly_bracket>\})    # bracket
            )
        )
      | (?P<code>
            "(?:\\.|[^"\\])*"            # double quoted string
          | '(?:\\.|[^'\\])*'            # single quoted string
          | .[^,"']*                     # everything else
        )
    """,
    re.MULTILINE | re.DOTALL | re.VERBOSE
)


def strip_dangling_commas(text, preserve_lines=False):
    regex = JSON_PATTERN

    def remove_comma(g, preserve_lines):
        if preserve_lines:
            # ,] -> ] else ,} -> }
            if g["square_comma"] is not None:
                return g["square_ws"] + g["square_bracket"]
            else:
                return g["curly_ws"] + g["curly_bracket"]
        else:
            # ,] -> ] else ,} -> }
            return g["square_bracket"] if g["square_comma"] else g["curly_bracket"]

    def evaluate(m, preserve_lines):
        g = m.groupdict()
        return remove_comma(g, preserve_lines) if g["code"] is None else g["code"]

    return ''.join(map(lambda m: evaluate(m, preserve_lines), regex.finditer(text)))


def strip_comments(text, preserve_lines=False):
    return Comments('json', preserve_lines).strip(text)


def sanitize_json(text, preserve_lines=False):
    return strip_dangling_commas(Comments('json', preserve_lines).strip(text), preserve_lines)
