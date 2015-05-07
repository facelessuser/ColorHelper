"""
File Strip
Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
"""

import re

LINE_PRESERVE = re.compile(r"\r?\n", re.MULTILINE)
CPP_PATTERN = re.compile(
    r"""
        (?P<comments>
            /\*[^*]*\*+(?:[^/*][^*]*\*+)*/  # multi-line comments
          | \s*//(?:[^\r\n])*               # single line comments
        )
      | (?P<code>
            "(?:\\.|[^"\\])*"               # double quotes
          | '(?:\\.|[^'\\])*'               # single quotes
          | .[^/"']*                        # everything else
        )
    """,
    re.VERBOSE | re.MULTILINE | re.DOTALL
)
PY_PATTERN = re.compile(
    r"""
        (?P<comments>
            \s*\#(?:[^\r\n])*               # single line comments
        )
      | (?P<code>
            "{3}(?:\\.|[^\\])*"{3}          # triple double quotes
          | '{3}(?:\\.|[^\\])*'{3}          # triple single quotes
          | "(?:\\.|[^"\\])*"               # double quotes
          | '(?:\\.|[^'])*'                 # single quotes
          | .[^\#"']*                       # everything else
        )
    """,
    re.VERBOSE | re.MULTILINE | re.DOTALL
)


def _strip_regex(pattern, text, preserve_lines):
    def remove_comments(group, preserve_lines=False):
        return ''.join([x[0] for x in LINE_PRESERVE.findall(group)]) if preserve_lines else ''

    def evaluate(m, preserve_lines):
        g = m.groupdict()
        return g["code"] if g["code"] is not None else remove_comments(g["comments"], preserve_lines)

    return ''.join(map(lambda m: evaluate(m, preserve_lines), pattern.finditer(text)))


def _cpp(self, text, preserve_lines=False):
    return _strip_regex(
        CPP_PATTERN,
        text,
        preserve_lines
    )


def _python(self, text, preserve_lines=False):
    return _strip_regex(
        PY_PATTERN,
        text,
        preserve_lines
    )


class CommentException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Comments(object):
    styles = []

    def __init__(self, style=None, preserve_lines=False):
        self.preserve_lines = preserve_lines
        self.call = self.__get_style(style)

    @classmethod
    def add_style(cls, style, fn):
        if style not in cls.__dict__:
            setattr(cls, style, fn)
            cls.styles.append(style)

    def __get_style(self, style):
        if style in self.styles:
            return getattr(self, style)
        else:
            raise CommentException(style)

    def strip(self, text):
        return self.call(text, self.preserve_lines)

Comments.add_style("c", _cpp)
Comments.add_style("json", _cpp)
Comments.add_style("cpp", _cpp)
Comments.add_style("python", _python)
