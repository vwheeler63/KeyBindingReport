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

To be potentially conflicting, 2 key bindings must:

- involve the same keypress or keypress sequence, i.e.
  ``(binding1.keypress_tuple() == binding2.keypress_tuple()``

  and

- have a functionally-equivalent context condition.


Testing for Functionally-Equivalent Context Conditions
------------------------------------------------------
To detect 2 functionally-equivalent context conditions, the approach
taken is to make each condition have a "hash value" that is computed
and stored at instantiation time.  It encapsulates:

+----------------------------------+------+-------------------------+
| Description                      | Bits | Source                  |
+==================================+======+=========================+
| key (test) name (28 tests with   | 5    | Condition's entry # in  |
| "setting.xxx" counting as 1)     |      | _context_tests_by_name  |
+----------------------------------+------+-------------------------+
| operator (there are 6 operators) | 3    | _operator_codes_by_name |
+----------------------------------+------+-------------------------+
| operand type (str, bool, int)    | 2    | OperandTypeCode         |
+----------------------------------+------+-------------------------+
| match_all value                  | 1    | 0 == False, 1 == True   |
+----------------------------------+------+-------------------------+

To make it easy for humans to read in hex while debugging, each of the 4
values above could simply occupy a byte in a 32-bit integer.  The smaller
ones could occupy a nibble if needed.

Each ContextCondition has a "setting_name" attribute which is an empty
string by default.  If its test name begins with "setting.", then the
condition name is copied into it.  Then two ContextCondition objects
would be functionally equivalent if:

- they have the same hash value (ensuring the operands are of the same type)
- cond1.setting_name == cond2.setting_name.
- cond1.operand == cond2.operand, and

Note that this would also require the ContextCondition (at instantiation
time) to assume the default values for operator, operand and match_all
when they were not specified.


Testing for Functionally-Equivalent Contexts
--------------------------------------------
Over and above having context conditions that are functionally equivalent,
the order they may appear in another context is random, so there has to be
a way of:

- detecting if a condition is a functional equivalent of any number of
  other conditions, and then
- if true, preventing that "other" condition from being used in a
  subsequent functional-equivalence tests until the overall test is
  concluded.

The latter can be done by creating a local list of references to
the list of other conditions being tested, and when paired and tested,
can be eliminated from the local list so it is not used again in other
functional-equivalence tests.



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
    #     '_source',
    # ]

    def __init__(self, decoded_key_binding: dict, source: str):
        """
        :param decoded_key_binding:  key binding decoded from JSON in .sublime-keymap
        :param path:                 for improved debug output
        """
        self.update(decoded_key_binding)
        self._smart_context: smart_context.SmartContext | None = None

        if _context_key in decoded_key_binding:
            self._smart_context = smart_context.SmartContext(self)

        self._source = source

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
            result = f'{indent}source: {self._source}\n'
        else:
            result = ''

        cmd_as_func = self.command_as_function_repr()
        keypresses_json = json.dumps(self["keys"])
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
        return len(self[_keys_key])

    def keypress_list(self) -> list[str]:
        return self[_keys_key]

    def keypress_tuple(self) -> tuple[str]:
        return tuple(self[_keys_key])

    def keypresses_json(self) -> str:
        return json.dumps(self[_keys_key])

    def keypresses_repr(self) -> str:
        return repr(self[_keys_key])

    def command(self) -> str:
        return self[_command_key]

    def command_json(self) -> str:
        return json.dumps(self[_command_key])

    def command_repr(self) -> str:
        return repr(self[_command_key])

    def has_args(self) -> bool:
        return (( _args_key in self ))

    def args_dict(self) -> CommandArgs:
        result = None

        if _args_key in self:
            result = self[_args_key]

        return result

    def args_json(self) -> str:
        result = ''

        if _args_key in self:
            result = json.dumps(self[_args_key])

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

    def context_list(self) -> list[dict] | None:
        result = None

        if _context_key in self:
            result = self[_context_key]

        return result

    def context_json(self) -> str:
        result = ''

        if _context_key in self:
            result = json.dumps(self[_context_key])

        return result

    def context_formatted_json(self) -> str:
        result = ''

        if _context_key in self:
            result = json.dumps(self[_context_key], indent=2)

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
        cmd            = self.command()
        args           = self.args_dict()
        ctxt           = self.context_list()
        src            = self.source()

        return keypress_tuple, cmd, args, ctxt, src

