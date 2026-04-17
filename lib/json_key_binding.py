"""
JSON Key Binding Utilities, using data structures specific to
Sublime Text ``.sublime-keymap`` files.
"""

__all__ = ['condition_repr', 'binding_repr']


def condition_repr(condition: dict, longest_key_len: int = 0, longest_op_len: int = 0, indent_level: int = 0) -> str:
    """
    Python representation of ``json_binding`` context conditions (same structure as
    in .sublime-keymap files) such that the keys and values are in logical order.

    Each condition presented on 1 line.

    Representation (just one of these, but 2 shown to show meaning of args:
    -----------------------------------------------------------------------
        { "key": "selection_empty"           , "operator": "equal", "operand": False, "match_all": True }
        { "key": "setting.auto_match_enabled", "operator": "equal", "operand": True }
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^                ^^^^^
                      +-- longest_key_len                     +-- longest_op_len
    }
    """
    cond_name = condition['key']
    field = f'"{cond_name}"'
    indent = ' ' * indent_level
    result = f'{indent}{{ "key": {field:{longest_key_len + 2}}'

    if 'operator' in condition:
        op_name = condition["operator"]
        field = f'"{op_name}"'
        result += f', "operator": {field:{longest_op_len + 2}}'
    if 'operand' in condition:
        # This value can be str, bool or int, so we use `repr()`.
        result += f', "operand": {repr(condition["operand"])}'
    if 'match_all' in condition:
        result += f', "match_all": {repr(condition["match_all"])}'

    result += ' }'

    return result


def binding_repr(json_binding: dict, indent_level: int = 0) -> str:
    """
    Python representation of ``json_binding`` (same structure as in
    .sublime-keymap files) such that the keys and values are in logical order.

    Representation:
    ---------------
    json_binding={ "keys": ['('], "command": "insert_snippet"
      "args": {'contents': '(${0:$SELECTION})'}
      "context": [
        { "key": "setting.auto_match_enabled", "operator": "equal", "operand": True }
        { "key": "selection_empty"           , "operator": "equal", "operand": False, "match_all": True }
      ]
    }
    """
    indent = ' ' * indent_level
    result = f'json_binding={{ "keys": {repr(json_binding["keys"])}, "command": "{json_binding["command"]}"\n'

    if 'args' in json_binding:
        args_str = repr(json_binding['args'])
        result += f'    "args": {args_str}\n'

    if 'context' in json_binding:
        result += '    "context": [\n'
        ctx = json_binding['context']  # list of condition dictionaries
        longest_key_len = 0
        longest_op_len = 5   # Length of 'equal'

        for condition in ctx:
            key_len = len(condition['key'])
            if key_len > longest_key_len:
                longest_key_len = key_len
            if 'operator' in condition:
                op_len  = len(condition['operator'])
                if op_len > longest_op_len:
                    longest_op_len = op_len

        for condition in ctx:
            result += condition_repr(
                    condition,
                    longest_key_len,
                    longest_op_len,
                    indent_level + 2
                    ) + '\n'

        result += '    ]\n'

    result += '  }'

    return result
