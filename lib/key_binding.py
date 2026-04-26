from typing import List, Tuple, Optional
from . import context


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
    # __slots__ = [
    #     'context',
    #     'pkg_name',
    #     'file_name',
    # ]

    def __init__(self, decoded_key_binding: dict, pkg_name: str, file_name: str):
        """
        :param decoded_key_binding:  key binding decoded from JSON in .sublime-keymap
        :param path:                 for improved debug output
        """
        self.update(decoded_key_binding)

        if 'context' in decoded_key_binding:
            self.smart_context = context.Context(self)
        else:
            self.smart_context = None

        self.pkg_name = pkg_name
        self.file_name = file_name

    def __str__(self):
        return self.format_binding()

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
        return f'<{self.__class__.__name__} {self.format_binding()}>'

    def format_binding(self, indent_level: int = 0, include_extra: bool = False) -> str:
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
        if include_extra:
            result = f'{indent}source: {self.pkg_name}/{self.file_name}\n'
        else:
            result = ''

        cmd_as_func = self.command_as_function_repr()
        result += f'{indent}{{ {repr(self["keys"])}, {cmd_as_func}'

        if self.smart_context:
            result += '\n' + self.smart_context.format_context(indent_level + 1)
            result += f'\n{indent}}}'
        else:
            result += ' }'

        return result

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

    def has_args(self) -> bool:
        return (( 'args' in self ))

    def args(self) -> Optional[dict]:
        result = None

        if 'args' in self:
            result = self['args']

        return result

    def command_as_function_repr(self) -> str:
        command = self['command']
        args_repr = ''
        if 'args' in self:
            args_repr = repr(self['args'])
        return f'{command}({args_repr})'

    def has_context(self) -> bool:
        return (( self.smart_context is not None ))

    def decoded_context(self) -> Optional[list]:
        result = None

        if 'context' in self:
            result = self['context']

        return result

    def smart_context(self) -> Optional[list]:
        return self.smart_context

    def package_name(self) -> str:
        return self.pkg_name

    def keymap_file_name(self) -> str:
        return self.file_name

    def parts(self) -> Tuple[List[str], str, dict, List[dict]]:
        """
        Parts of JSON Key-Binding object, extracted as:

        - keys    :   Tuple[str]   (e.g. ("alt+up"))
        - command :   str          (e.g. 'box_drawing_draw_one_character')
        - args    :   dict or None (e.g. {'direction': 0, 'line_count': 1})
        - context :   List[dict]   (e.g. [{'key': 'box_drawing.ok_to_draw', 'match_all': True}])
        - pkg_name:   str
        - file_name:  str

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

        return keys, cmd, args, ctxt, self.pkg_name, self.file_name

