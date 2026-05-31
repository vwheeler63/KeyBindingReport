""" -----------------------------------------------------------------------
reStructuredText Python utilities.
----------------------------------------------------------------------- """


_rst_chars_to_escape_in_table = [
    '\\',  # Otherwise, lone '\' escapes the space ahead of it.
    '`',   # Otherwise Docutils tries to start a default interpreted-text role.
    '-',   # Otherwise Docutils interprets as a bullet
    '+',   # Otherwise Docutils interprets as a bullet
    '*',   # Otherwise Docutils interprets as a bullet
    '|',   # Otherwise Docutils interprets as signal to line break
    "'",   # Otherwise Docutils converts it to an opening "smart quote" (curved).
    '"',   # Otherwise Docutils converts it to an opening "smart quote" (curved).
]


def rst_escaped_for_table(input_str: str) -> str:
    result = input_str

    for c in _rst_chars_to_escape_in_table:
        if c in result:
            escaped_c = '\\' + c
            result = result.replace(c, escaped_c)

    return result


def rst_encapsulate_as_literal(input_str: str) -> str:
    return '``' + input_str + '``'


def rst_encapsulate_as_keyboard_role(input_str: str) -> str:
    return f':kbd:`{input_str}`'

