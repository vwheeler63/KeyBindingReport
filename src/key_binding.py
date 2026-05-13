"""************************************************************************
KeyBinding
**********



KeyBinding Terminology
======================

These KeyBindings are objects from the lists in `.sublime-keymap` files,
so all terminology related to those key binding objects is used herein.


KeyBinding Design
=================

A.  There is a concept of a KeyBinding object.

    1.  It has:
        +   source
            +   PackageName/Default ($platform).sublime-keymap, or
            +   PackageName/Default.sublime-keymap
        +   _smart_context
            +   SmartContext objects
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
    3.  It can be requested to change KeyBinding objects as follows:
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...


KeyBinding Data Flow
====================

KeyBinding is in the inheritance tree to ReportKeyBinding class.
ReportKeyBinding objects are used to populate 2 data structures
used to generate reports, and to provide data for utilities that
deal with Sublime Text Key Bindings.


Detecting Potentially-Conflicting Key Bindings
==============================================

See ``can_override()`` docstring.



@version  Current revision:  @(#) v1.0  04-May-2026 18:11
@version  1.0  04-May-2026 18:11  vw  - Created.
***************************************************************************"""

import json
from sublime_types import CommandArgs
from . import smart_context



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

class KeyBinding:
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
    __slots__ = [
        '_smart_context',   # None if binding had no "context" entry.
        '_source',
        'source_entry_no',
        '_keys',
        '_command',
        '_args',
        '_context',
        '_cached_keypress_tuple',
    ]

    def __init__(self, decoded_key_binding: dict, source: str, source_entry_no: int):
        """
        :param decoded_key_binding:  key binding decoded from JSON in .sublime-keymap
        :param path:                 for improved debug output
        """
        self._source = source
        self.source_entry_no = source_entry_no
        self._keys = decoded_key_binding[_keys_key]
        self._command = decoded_key_binding[_command_key]

        if _args_key in decoded_key_binding:
            self._args = decoded_key_binding[_args_key]
        else:
            self._args = None

        self._smart_context: smart_context.SmartContext | None = None

        if _context_key in decoded_key_binding:
            self._context = decoded_key_binding[_context_key]
            self._smart_context = smart_context.SmartContext(self)
        else:
            self._context = None

        self._cached_keypress_tuple = None

    def __str__(self):
        return self.formatted()

    def __repr__(self):
        """
        KeyBinding({ ['right'], move({'by': 'characters', 'forward': true}) })

        or if there is a "context" entry:

        KeyBinding({ ['"'], move({'by': 'characters', 'forward': true})
          "context": [
            { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": true }
            { "key": "selection_empty"           , "operator": "equal"         , "operand": true, "match_all": true }
            { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": true }
            { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": true }
            { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": true }
          ]
        })

        """
        return f'{self.__class__.__name__}({self.formatted()})'

    def applies_in_same_context(self, other) -> bool:
        """ Does ``other`` apply in the same context as ``self``? """
        result = False

        if self._smart_context is None and other._smart_context is None:
            result = True
        elif self._smart_context and other._smart_context:
            result = self._smart_context.is_equivalent(other._smart_context)

        return result

    def can_override(self, other) -> bool:
        """
        To be able to override ``other``, ``self`` and ``other`` must:

        - involve the same keypresses, i.e.
          ``self.keypress_tuple() == other.keypress_tuple()``,

          and

        - have an equivalent context.
        """
        result = False

        if self.keypress_tuple() == other.keypress_tuple():
            result = self.applies_in_same_context(other)

        return result

    def formatted(self, indent_level: int = 0, include_source: bool = False) -> str:
        """
        Python representation of ``self`` (same structure as in
        .sublime-keymap files) such that the keys and values are in logical order.

        Representation:
        ---------------
        { ['right'], move({'by': 'characters', 'forward': true}) }

        or if there is a "context" entry:

        { ['"'], move({'by': 'characters', 'forward': true})
          "context": [
            { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": true }
            { "key": "selection_empty"           , "operator": "equal"         , "operand": true, "match_all": true }
            { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": true }
            { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": true }
            { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": true }
          ]
        }
        """
        indent = '  ' * indent_level
        if include_source:
            result = f'{indent}source: {self._source}  (entry {self.source_entry_no})\n'
        else:
            result = ''

        cmd_as_func = self.command_as_function_repr()
        keypresses_json = json.dumps(self._keys)
        result += f'{indent}{{ {keypresses_json}, {cmd_as_func}'

        if self._smart_context:
            result += '\n' + self.readable_context_repr(indent_level + 1)
            result += f'\n{indent}}}'
        else:
            result += ' }'

        return result

    def keypress_count(self) -> int:
        """
        Number of keypresses in binding.
        """
        return len(self._keys)

    def keypress_list(self) -> list[str]:
        return self._keys

    def keypress_tuple(self) -> tuple[str]:
        if self._cached_keypress_tuple is None:
            self._cached_keypress_tuple = tuple(self._keys)
        return self._cached_keypress_tuple

    def keypresses_json(self) -> str:
        return json.dumps(self._keys)

    def keypresses_repr(self) -> str:
        return repr(self._keys)

    def command(self) -> str:
        return self._command

    def command_json(self) -> str:
        return json.dumps(self._command)

    def command_repr(self) -> str:
        return repr(self._command)

    def has_args(self) -> bool:
        return (( self._args is not None ))

    def args_dict(self) -> CommandArgs:
        return self._args

    def args_json(self) -> str:
        result = ''

        if self._args is not None:
            result = json.dumps(self._args)

        return result

    def args_repr(self) -> str:
        result = ''

        if self._args is not None:
            result = repr(self._args)

        return result

    def command_as_function_repr(self) -> str:
        command = self._command
        args_repr = self.args_repr()
        return f'{command}({args_repr})'

    def has_context(self) -> bool:
        return (( self._smart_context is not None ))

    def context_list(self) -> list[dict] | None:
        return self._context

    def context_json(self) -> str:
        result = ''

        if self._context is not None:
            result = json.dumps(self._context)

        return result

    def context_formatted_json(self) -> str:
        result = ''

        if self._context is not None:
            result = json.dumps(self._context, indent=2)

        return result

    def smart_context(self) -> smart_context.SmartContext | None:
        return self._smart_context

    def readable_context_repr(self, indent_level: int = 0) -> str:
        if self._smart_context:
            result = self._smart_context.formatted(indent_level)
        else:
            result = ''

        return result

    def source(self) -> str:
        return self._source

    def parts(self) -> tuple[tuple, str, CommandArgs, list[dict] | None, str]:
        """
        Parts of JSON Key-Binding object, extracted as:

        - keys   :   tuple[str]   (e.g. ("alt+up"))
        - command:   str          (e.g. 'box_drawing_draw_one_character')
        - args   :   dict or None (e.g. {'direction': 0, 'line_count': 1})
        - context:   list[dict]   (e.g. [{'key': 'box_drawing.ok_to_draw', 'match_all': true}])
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
        keypress_tuple = self.keypress_tuple()
        cmd            = self._command
        args           = self._args
        ctxt           = self._context
        src            = self._source

        return keypress_tuple, cmd, args, ctxt, src
