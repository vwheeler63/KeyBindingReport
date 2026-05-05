"""************************************************************************
KeyBinding
**********



key_binding Terminology
=============================

These KeyBindings are objects from the lists in `.sublime-keymap` files,
so all terminology related to those key binding objects is used herein.


key_binding Design
========================

A.  There is a concept of a key_binding object.

    1.  It has:
        +   source
            +   PackageName/Default ($platform).sublime-keymap, or
            +   PackageName/Default.sublime-keymap
        +   _smart_context
            +   Context objects
        +   ...
    2.  It can be asked:
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
    3.  It can be requested to change key_binding objects as follows:
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...


key_binding Data Flow
===========================

KeyBinding is in the inheritance tree to ReportKeyBinding class.
ReportKeyBinding objects are used to populate 2 data structures
used to generate reports and to provide data for utilities that
deal with Sublime Text Key Bindings.



@version  Current revision:  @(#) v1.0  04-May-2026 18:11
@version  1.0  04-May-2026 18:11  vw  - Created.
***************************************************************************"""

from typing import List
from . import context



# *************************************************************************
# Configuration
# *************************************************************************



# *************************************************************************
# Constants
# *************************************************************************

_keys_key    = 'keys'
_command_key = 'command'
_args_key    = 'args'
_context_key = 'context'



# *************************************************************************
# Data
# *************************************************************************



# *************************************************************************
# Utilities
# *************************************************************************



# *************************************************************************
# Function Definitions
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

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
    #     '_smart_context',
    #     'source',
    # ]

    def __init__(self, decoded_key_binding: dict, source: str):
        """
        :param decoded_key_binding:  key binding decoded from JSON in .sublime-keymap
        :param path:                 for improved debug output
        """
        self.update(decoded_key_binding)
        self._smart_context: context.Context | None = None

        if _context_key in decoded_key_binding:
            self._smart_context = context.Context(self)

        self.source = source

    def __str__(self):
        return self.formatted()

    def __repr__(self):
        """
        KeyBinding({ ['right'], move({'by': 'characters', 'forward': True}) })

        or if there is a "context" entry:

        KeyBinding({ ['"'], move({'by': 'characters', 'forward': True})
          "context": [
            { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": True }
            { "key": "selection_empty"           , "operator": "equal"         , "operand": True, "match_all": True }
            { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": True }
            { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": True }
            { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": True }
          ]
        })

        """
        return f'{self.__class__.__name__}({self.formatted()})'

    def formatted(self, indent_level: int = 0, include_extra: bool = False) -> str:
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
            result = f'{indent}source: {self.source}\n'
        else:
            result = ''

        cmd_as_func = self.command_as_function_repr()
        result += f'{indent}{{ {repr(self["keys"])}, {cmd_as_func}'

        if self._smart_context:
            result += '\n' + self._smart_context.formatted(indent_level + 1)
            result += f'\n{indent}}}'
        else:
            result += ' }'

        return result

    def keypress_count(self) -> int:
        """
        Number of keypresses in binding.
        """
        return len(self[_keys_key])

    def keys_as_list(self) -> list:
        return self[_keys_key]

    def keys_as_tuple(self) -> tuple:
        return tuple(self[_keys_key])

    def command(self) -> str:
        return self[_command_key]

    def has_args(self) -> bool:
        return (( _args_key in self ))

    def args(self) -> dict | None:
        result = None

        if _args_key in self:
            result = self[_args_key]

        return result

    def args_repr(self) -> str:
        result = ''

        if _args_key in self:
            result = repr(self[_args_key])

        return result

    def command_as_function_repr(self) -> str:
        command = self[_command_key]
        args_repr = self.args_repr()
        return f'{command}({args_repr})'

    def has_context(self) -> bool:
        return (( self._smart_context is not None ))

    def decoded_context(self) -> list | None:
        result = None

        if _context_key in self:
            result = self[_context_key]

        return result

    def smart_context(self) -> context.Context | None:
        return self._smart_context

    def source_file(self) -> str:
        return self.source

    def parts(self) -> tuple[tuple, str, dict | None, List[dict] | None]:
        """
        Parts of JSON Key-Binding object, extracted as:

        - keys   :   tuple[str]   (e.g. ("alt+up"))
        - command:   str          (e.g. 'box_drawing_draw_one_character')
        - args   :   dict or None (e.g. {'direction': 0, 'line_count': 1})
        - context:   List[dict]   (e.g. [{'key': 'box_drawing.ok_to_draw', 'match_all': True}])
        - source :   str

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
        keypress_tuple = tuple(json_binding[_keys_key])
        cmd  = json_binding[_command_key]

        if _args_key in json_binding:
            args = json_binding[_args_key]
        else:
            args = None

        if _context_key in json_binding:
            ctxt = json_binding[_context_key]
        else:
            ctxt = None

        return keypress_tuple, cmd, args, ctxt, self.source

