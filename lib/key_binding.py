from typing import List, Tuple, Optional


class KeyBinding(dict):
    """
    Key-binding objects from a ``.sublime-keymap`` file.

    {
        "keys": "[<keypress_list>]",
        "command": "<command_name>",
        "args": {...}        // Optional:  required only if command requires it;
                             //            key names must match command arg names.
        "context": [         // Optional:  limits contexts in which binding will be applied.
            {<condition>},
            ...
        ]
    }
    """
    def __init__(self, decoded_key_binding: dict):
        self.update(decoded_key_binding)

    def __str__(self):
        return f'<{self.__class__.__name__} {self.binding_repr()}>'

    def __repr__(self):
        """
        <KeyBinding pkg=Default { ['right'], move({'by': 'characters', 'forward': True}) }>

        or if there is a "context" entry:

        <KeyBinding pkg=Default { ['"'], move({'by': 'characters', 'forward': True})
          "context": [
            { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": True }
            { "key": "selection_empty"           , "operator": "equal"         , "operand": True, "match_all": True }
            { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": True }
            { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": True }
            { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": True }
          ]
        }>

        """
        return f'<{self.__class__.__name__} {self.binding_repr()}>'

    def keypress_count(self) -> int:
        """
        Number of keypresses in binding.
        """
        return len(self['keys'])

    def keys(self) -> list:
        return self['keys']

    def keys_as_tuple(self) -> tuple:
        return tuple(self['keys'])

    def command(self) -> str:
        return self['command']

    def args(self) -> Optional[dict]:
        result = None

        if 'args' in self:
            result = self['args']

        return result

    def context(self) -> Optional[list]:
        result = None

        if 'context' in self:
            result = self['context']

        return result

    def parts(self) -> Tuple[List[str], str, dict, List[dict]]:
        """
        Parts of JSON Key-Binding object, extracted as:

        - keys   :  Tuple[str]   (e.g. ("alt+up"))
        - command:  str          (e.g. 'box_drawing_draw_one_character')
        - args   :  dict or None (e.g. {'direction': 0, 'line_count': 1})
        - context:  List[dict]   (e.g. [{'key': 'box_drawing.ok_to_draw', 'match_all': True}])

        Examples above use this JSON binding as input:
        {
            "keys": ["alt+up"],
            "command": "box_drawing_draw_one_character",
            "args": {
                "line_count": 1,
                "direction": 0,
            },
            "context": [
                { "key": "box_drawing.ok_to_draw", "match_all": true },
            ]
        },
        """
        json_binding = self
        keys = tuple(json_binding['keys'])
        cmd  = json_binding['command']

        if 'args' in json_binding:
            args = json_binding['args']
        else:
            args = None

        if 'context' in json_binding:
            ctxt = json_binding['context']
        else:
            ctxt = None

        return keys, cmd, args, ctxt

    def binding_repr(self, indent_level: int = 0) -> str:
        """
        Python representation of ``self`` (same structure as in
        .sublime-keymap files) such that the keys and values are in logical order.

        Representation:
        ---------------
        { ['right'], move({'by': 'characters', 'forward': True}) }

        or if there is a "context" entry:

        { ['"'], move({'by': 'characters', 'forward': True})
          "context": [
            { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": True }
            { "key": "selection_empty"           , "operator": "equal"         , "operand": True, "match_all": True }
            { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": True }
            { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": True }
            { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": True }
          ]
        }
        """
        indent = '  ' * indent_level
        cmd_as_func = self.command_as_function_repr()
        result = f'{indent}{{ {repr(self["keys"])}, {cmd_as_func}'

        if 'context' in self:
            result += f'\n{indent}  "context": [\n'
            ctxt = self['context']  # list of condition dictionaries
            longest_key_len = 0
            longest_op_len = 5   # Length of 'equal'

            # Compute length of widest `key` and `operator` fields.
            for condition in ctxt:
                key_len = len(condition['key'])
                if key_len > longest_key_len:
                    longest_key_len = key_len
                if 'operator' in condition:
                    op_len  = len(condition['operator'])
                    if op_len > longest_op_len:
                        longest_op_len = op_len

            # Now produce formatted string.
            for condition in ctxt:
                result += self.condition_repr(
                        condition,
                        longest_key_len,
                        longest_op_len,
                        indent_level + 2
                        ) + '\n'

            result += f'{indent}  ]\n'
            result += f'{indent}}}'
        else:
            result += ' }'

        return result

    def command_as_function_repr(self) -> str:
        command = self['command']
        args_repr = ''
        if 'args' in self:
            args_repr = repr(self['args'])
        return f'{command}({args_repr})'

    def condition_repr(self, condition: dict, longest_key_len: int = 0, longest_op_len: int = 0, indent_level: int = 0) -> str:
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
        indent = '  ' * indent_level
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
