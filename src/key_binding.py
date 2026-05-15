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
from typing import Iterable
from enum import IntFlag
from sublime_types import CommandArgs, Value
from . import smart_context
from . import platform



# *************************************************************************
# Configuration
# *************************************************************************



# *************************************************************************
# Constants
# *************************************************************************

class ModifierKeyBits(IntFlag):
    SHIFT         = 0b0001
    CTRL          = 0b0010
    ALT           = 0b0100
    COMMAND       = 0b1000

    NONE          = 0b0000
    ALL           = 0b1111
    ANY           = 0b1111


_keys_key    = 'keys'
_command_key = 'command'
_args_key    = 'args'
_context_key = 'context'

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



# *************************************************************************
# Data
# *************************************************************************



# *************************************************************************
# Utilities
# *************************************************************************

def rst_escaped(input_str: str) -> str:
    result = input_str

    for c in _rst_chars_to_escape_in_table:
        if c in result:
            escaped_c = '\\' + c
            result = result.replace(c, escaped_c)

    return result


def main_key_and_mod_key_list(keypress_str: str) -> tuple[str, list[str]]:
    """
    Main key and modifier-key list

    :param keypress_str:  Keypress definition string compatible with
                            Sublime Text `.sublime-keymap` "keys" entries.
                            Example:  "ctrl+shift+p"

    IMPORTANT:  This function is here at module level because not all
    reports are accomplished by building a data structure with KeyBinding
    objects.  Example:  Keys-Used report doesn't need anything beyond the
    keypress strings in the bindings, and so does not undergo the overhead
    of building KeyBinding and SmartContext objects because they simply
    aren't needed.  This function serves that report.
    """
    if keypress_str.endswith('++'):
        main_key_name     = '+'
        mod_key_name_list = keypress_str[:-2].split('+')
    else:
        key_list          = keypress_str.split('+')
        main_key_name     = key_list.pop()
        mod_key_name_list = key_list

    return main_key_name, mod_key_name_list


def main_key_and_modifier_code(keypress_str: str) -> tuple[str, int]:
    """
    Key-modifier code from `keypress_str` (e.g. "ctrl+alt+shift+p").

    :param keypress_str:  Keypress definition string compatible with
                            Sublime Text `.sublime-keymap` "keys" entries

    See "key-modifier code" and "encoded keypress" in definitions in
    module docstring for details.

    IMPORTANT!  ``keypress_str.split('+')`` is not adequate logic by itself
    because we have valid ``keypress_str`` values that look like
    this: "ctrl++".

    IMPORTANT:  This function is here at module level because even the main
    report that uses KeyBinding and SmartContext objects, has modes where
    it filters out a large amount of key bindings that DO NOT have to have
    those classes instantiated, and it is cheaper to computer merely the
    main key and modification code than instantiate KeyBinding, Keypress
    and SmartContext objects.  So this used (at this writing) in 4 places
    where the wise design choice is to NOT undergo that overhead.

                                    OSX       Win/Linux
    | #   shift   # |
    | #   ctrl    # | <------------------------------+
    | #    alt    # | <-------------+                |
    | #  command  # | <-------------|--+--------+    |
    |    option     | Mac's 'alt' --+  |      [Win]  |
    |     super     | -----------------+--------+    |
    |    primary    | -----------------+-------------+
    """
    modifier_code = 0
    main_key_name, mod_key_name_list = main_key_and_mod_key_list(keypress_str)

    for mod_key in mod_key_name_list:
        if mod_key == 'shift':
            modifier_code |= ModifierKeyBits.SHIFT
        elif mod_key in ['ctrl', 'control']:
            modifier_code |= ModifierKeyBits.CTRL
        elif mod_key in ['alt', 'option']:
            modifier_code |= ModifierKeyBits.ALT
        elif mod_key in ['super', 'command']:
            # Command key on OSX, Windows key on Windows and Linux.
            # Either way we record this as "COMMAND" bit.
            modifier_code |= ModifierKeyBits.COMMAND
        elif mod_key == 'primary':
            if platform.is_osx():
                modifier_code |= ModifierKeyBits.COMMAND
            else:
                modifier_code |= ModifierKeyBits.CTRL
        else:
            raise AssertionError(f'{__package__}.main_key_and_modifier_code(): modifier key unrecognized: [{mod_key}].')

    return main_key_name, modifier_code


# def modifier_repr(modifier_code: int) -> str:
#     modifiers = []
#     if modifier_code & ModifierKeyBits.CTRL:
#         modifiers.append('ctrl')
#     if modifier_code & ModifierKeyBits.ALT:
#         modifiers.append('alt')
#     if modifier_code & ModifierKeyBits.SHIFT:
#         modifiers.append('shift')
#     return '+'.join(modifiers)


# def keypress_repr(main_key_name: str, modifier_code: int) -> str:
#     """ This is the reverse of ``main_key_and_modifier_code(str)``. """
#     if modifier_code:
#         mod_repr = modifier_repr(modifier_code)
#         keypr_repr = f'{mod_repr}+{main_key_name}'
#     else:
#         keypr_repr = f'{main_key_name}'

#     result = f'[{keypr_repr}]'
#     return result


# def encoded_keypress_from_components(main_key_name: str, modifier_code: int) -> int:
#     """
#     Encoded keypress from `main_key_name` and `modifier_code`.

#     :param main_key_name:       Official name of key, found in `all_key_names`.
#                                   (See Key Names in module docstring for the list.)
#     :param modifier_code:   Integer representation of Ctrl+Alt+Shift key
#                                   modifiers accommodating keypress.
#                                   (See "key-modifier code" and "encoded keypress"
#                                   in definitions in module docstring for details.)
#     """
#     result = -1

#     if main_key_name in key_index_by_key_name_dict:
#         i = key_index_by_key_name_dict[main_key_name]
#         result = (i << 4) | modifier_code

#     return result


# def encoded_keypress(keypress_str: str) -> int:
#     """
#     Encoded keypress from `keypress_str` (e.g. "ctrl+alt+shift+p").

#     :param keypress_str:  Keypress definition string compatible with
#                             Sublime Text `.sublime-keymap` "keys" entries

#     See "key-modifier code" and "encoded keypress" in definitions in
#     module docstring for details.
#     """
#     kn, mod_code = main_key_and_modifier_code(keypress_str)
#     return encoded_keypress_from_components(kn, mod_code)


def modifier_flag_characters(modifier_code: int, mod_applies_char: str) -> tuple[str, str, str, str]:
    """
    Tuple of ``mod_applies_char`` or space characters based on ``ModifierKeyBits``
    set in ``modifier_code``.  Example:

    - ' ', ' ', ' ', ' ' <= no modifiers
    - ' ', ' ', ' ', 'x' <=                    Shift modifier
    - ' ', ' ', 'x', ' ' <=             Ctrl         modifier
    - ' ', ' ', 'x', 'x' <=             Ctrl + Shift modifier
    - ' ', 'x', ' ', ' ' <=       Alt                modifier
    - ' ', 'x', ' ', 'x' <=       Alt +        Shift modifier
    - ' ', 'x', 'x', ' ' <=       Alt + Ctrl         modifier
    - ' ', 'x', 'x', 'x' <=       Alt + Ctrl + Shift modifier
    - 'x', ' ', ' ', ' ' <= Cmd                      modifier
    - 'x', ' ', ' ', 'x' <= Cmd +              Shift modifier
    - 'x', ' ', 'x', ' ' <= Cmd +       Ctrl         modifier
    - 'x', ' ', 'x', 'x' <= Cmd +       Ctrl + Shift modifier
    - 'x', 'x', ' ', ' ' <= Cmd + Alt                modifier
    - 'x', 'x', ' ', 'x' <= Cmd + Alt +        Shift modifier
    - 'x', 'x', 'x', ' ' <= Cmd + Alt + Ctrl         modifier
    - 'x', 'x', 'x', 'x' <= Cmd + Alt + Ctrl + Shift modifier

    It is by design that this *not* be the same sequence as the modifier
    keys appear in `.sublime-keymap` files.

    IMPORTANT:  the reason this is a module-level function is that some
    reports generate rows that include these flags when there is not an
    actual KEY BINDING, to show that there isn't!  But this tuple is
    still needed.  So it is the ONE location where this logic is, and
    the Keypress class calls this function.
    """
    space = ' '

    if modifier_code & ModifierKeyBits.SHIFT:
        S = mod_applies_char
    else:
        S = space

    if modifier_code & ModifierKeyBits.CTRL:
        C = mod_applies_char
    else:
        C = space

    if modifier_code & ModifierKeyBits.ALT:
        A = mod_applies_char
    else:
        A = space

    if modifier_code & ModifierKeyBits.COMMAND:
        W = mod_applies_char
    else:
        W = space

    return W, A, C, S



# *************************************************************************
# Function Definitions
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class Keypress:
    """
    Sublime Text Key-Binding Keypresses that dovetail in with
    KeyBindingReport Package data needs.

    See "key-modifier code" and "encoded keypress" in definitions in
    module docstring for details.

    All modifier keys map to the top 4:
    -----------------------------------

                                    OSX       Win/Linux
    | #   shift   # |
    | #   ctrl    # | <------------------------------+
    | #    alt    # | <-------------+                |
    | #  command  # | <-------------|--+--------+    |
    |    option     | Mac's 'alt' --+  |      [Win]  |
    |     super     | -----------------+--------+    |
    |    primary    | -----------------+-------------+
    """
    __slots__ = [
        'keypress_str',
        'main_key_name',
        'modifier_key_list',
        'modifier_code',
    ]

    def __init__(self, keypress_str: str):
        """
        :param keypress_str:  Keypress definition string directly with format
                                of `.sublime-keymap` "keys" entries,
                                e.g. "ctrl+alt+shift+p".

        IMPORTANT!  ``keypress_str.split('+')`` is not adequate logic by itself
        because we have valid ``keypress_str`` values that look like
        this: "ctrl++" => [Ctrl][+].

                                        OSX       Win/Linux
        | #   shift   # |
        | #   ctrl    # | <------------------------------+
        | #    alt    # | <-------------+                |
        | #  command  # | <-------------|--+--------+    |
        |    option     | Mac's 'alt' --+  |      [Win]  |
        |     super     | -----------------+--------+    |
        |    primary    | -----------------+-------------+
        """
        modifier_code = 0

        if keypress_str.endswith('++'):
            main_key_name             = '+'
            mod_key_name_list = keypress_str[:-2].split('+')
        else:
            key_list                  = keypress_str.split('+')
            main_key_name             = key_list.pop()
            mod_key_name_list = key_list

        for mod_key in mod_key_name_list:
            if mod_key == 'shift':
                modifier_code |= ModifierKeyBits.SHIFT
            elif mod_key in ['ctrl', 'control']:
                modifier_code |= ModifierKeyBits.CTRL
            elif mod_key in ['alt', 'option']:
                modifier_code |= ModifierKeyBits.ALT
            elif mod_key in ['super', 'command']:
                # Command key on OSX, Windows key on Windows and Linux.
                # Either way we record this as "COMMAND" bit.
                modifier_code |= ModifierKeyBits.COMMAND
            elif mod_key == 'primary':
                if platform.is_osx():
                    modifier_code |= ModifierKeyBits.COMMAND
                else:
                    modifier_code |= ModifierKeyBits.CTRL
            else:
                raise AssertionError(f'{__package__}.main_key_and_modifier_code(): modifier key unrecognized: [{mod_key}].')

        self.keypress_str      = keypress_str
        self.main_key_name     = main_key_name
        self.modifier_key_list = mod_key_name_list
        self.modifier_code     = modifier_code

    def human_friendly_repr(self):
        """ Ctrl=Alt-P """
        parts = []
        parts.extend(self.modifier_key_list)
        parts.append(self.main_key_name)
        return '-'.join(parts).title()

    def modifier_flag_characters(self, flag_char: str) -> tuple[str, str, str, str]:
        """
        Tuple of ``flag_char`` or space characters based on ``ModifierKeyBits``
        set in ``modifier_code``.  Example:

        - ' ', ' ', ' ', ' ' <= no modifiers
        - ' ', ' ', ' ', 'x' <=                    Shift modifier
        - ' ', ' ', 'x', ' ' <=             Ctrl         modifier
        - ' ', ' ', 'x', 'x' <=             Ctrl + Shift modifier
        - ' ', 'x', ' ', ' ' <=       Alt                modifier
        - ' ', 'x', ' ', 'x' <=       Alt +        Shift modifier
        - ' ', 'x', 'x', ' ' <=       Alt + Ctrl         modifier
        - ' ', 'x', 'x', 'x' <=       Alt + Ctrl + Shift modifier
        - 'x', ' ', ' ', ' ' <= Cmd                      modifier
        - 'x', ' ', ' ', 'x' <= Cmd +              Shift modifier
        - 'x', ' ', 'x', ' ' <= Cmd +       Ctrl         modifier
        - 'x', ' ', 'x', 'x' <= Cmd +       Ctrl + Shift modifier
        - 'x', 'x', ' ', ' ' <= Cmd + Alt                modifier
        - 'x', 'x', ' ', 'x' <= Cmd + Alt +        Shift modifier
        - 'x', 'x', 'x', ' ' <= Cmd + Alt + Ctrl         modifier
        - 'x', 'x', 'x', 'x' <= Cmd + Alt + Ctrl + Shift modifier

        It is by design that this *not* be the same sequence as the modifier
        keys appear in `.sublime-keymap` files.
        """
        return modifier_flag_characters(self.modifier_code, flag_char)



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
        '_source',
        'source_entry_no',
        '_keys',
        '_command',
        '_args',
        '_context',
        '_smart_context',   # None if binding had no "context" entry.
        '_cached_keypress_tuple',
        'keypresses',
    ]

    def __init__(self, decoded_key_binding: dict[str, Value], source: str, source_entry_no: int):
        """
        :param decoded_key_binding:  key binding decoded from JSON in .sublime-keymap
        :param path:                 for improved debug output

        By design, original decoded JSON values are kept
        """
        if _keys_key not in decoded_key_binding or _command_key not in decoded_key_binding:
            raise AssertionError(f'Invalid `decoded_key_binding` missing "keys" or "command" entry: {decoded_key_binding!r}')

        # -----------------------------------------------------------------
        # Keys
        # -----------------------------------------------------------------
        keys = decoded_key_binding[_keys_key]
        if keys is None or not isinstance(keys, list):
            raise AssertionError(f'Invalid `decoded_key_binding`: "keys" entry was {keys!r}')
        self._keys = keys

        keypresses: list[Keypress] = []
        for keypress_str in keys:
            if isinstance(keypress_str, str):
                keypresses.append(Keypress(keypress_str))
            else:
                raise AssertionError(f'Invalid `decoded_key_binding`: keypress entry was {keypress_str!r}')

        self.keypresses = keypresses
        #     TODO: use of ``Keypress`` has yet to prove that it simplifies
        #           code downstream.  At this writing (15-May-2026 12:47) it
        #           has only been a benefit in 1 place.  Review in a week or
        #           so to see if it really should be preserved, or if it should
        #           be relegated to the (necessary) module-level functions that
        #           already exist, e.g. ``main_key_and_modifier_code()``.

        # -----------------------------------------------------------------
        # Command
        # -----------------------------------------------------------------
        command = decoded_key_binding[_command_key]
        if command is None:
            raise AssertionError(f'Invalid `decoded_key_binding`: "command" entry was {command!r}')
        command = decoded_key_binding[_command_key]
        if isinstance(command, str):
            self._command = command

        # -----------------------------------------------------------------
        # Args
        # -----------------------------------------------------------------
        self._args: CommandArgs = None
        if _args_key in decoded_key_binding:
            args = decoded_key_binding[_args_key]
            if isinstance(args, dict):
                self._args = args

        # -----------------------------------------------------------------
        # Context
        # -----------------------------------------------------------------
        self._smart_context: smart_context.SmartContext | None = None

        if _context_key in decoded_key_binding:
            self._context = decoded_key_binding[_context_key]
            self._smart_context = smart_context.SmartContext(self)
        else:
            self._context = None

        # -----------------------------------------------------------------
        # Source
        # -----------------------------------------------------------------
        self._source = source
        self.source_entry_no = source_entry_no

        self._cached_keypress_tuple = None

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

        if self._args is not None:
            args_repr = self.args_json()
            result = f'{command}( {args_repr} )'
        else:
            result = f'{command}()'

        return result

    def has_context(self) -> bool:
        return (( self._smart_context is not None ))

    def context_list(self) -> list[dict] | None:
        return self._context

    def context_json(self) -> str:
        result = ''

        if self._context is not None:
            result = json.dumps(self._context)

        return result

    def context_original_json(self) -> str:
        result = ''

        if self._context is not None:
            result = json.dumps(self._context, indent=2)

        return result

    def context_readable_repr(self, indent_level: int = 0) -> str:
        if self._smart_context:
            result = self._smart_context.formatted(indent_level)
        else:
            result = ''

        return result

    def context_readable_minimal_repr(self, indent_level: int = 0) -> str:
        if self._smart_context:
            result = self._smart_context.formatted(indent_level, minimal=True)
        else:
            result = ''

        return result

    def smart_context(self) -> smart_context.SmartContext | None:
        return self._smart_context

    def source(self) -> str:
        return self._source

    def parts(self) -> tuple[tuple[str], str, CommandArgs, list[dict[str, Value]] | None, str]:
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
            result += '\n' + self.context_readable_repr(indent_level + 1)
            result += f'\n{indent}}}'
        else:
            result += ' }'

        return result

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


class ReportKeyBinding(KeyBinding):
    """
    Representation of a KeyBinding plus some additional data needed for reporting:

    - main_key_names
    - modifier_codes
    """
    # __slots__ = ['_smart_context', '_source', '_main_key_names', '_modifier_codes']

    def __init__(self, decoded_key_binding: dict[str, Value], source: str, source_entry_no: int):
        # Incorporate contents of `decoded_key_binding` into `self`.
        super().__init__(decoded_key_binding, source, source_entry_no)

        #self._main_key_names = []
        self._modifier_codes = []

        for keypress_str in self.keypress_list():
            main_key_name, mod_code = main_key_and_modifier_code(keypress_str)
            #self._main_key_names.append(main_key_name)
            self._modifier_codes.append(mod_code)

    def __repr__(self):
        """
        JSON Key Binding from Default Package:
        --------------------------------------
        { "keys": ["\""], "command": "move", "args": {"by": "characters", "forward": true}, "context":
            [
                { "key": "setting.auto_match_enabled", "operator": "equal", "operand": true },
                { "key": "selection_empty", "operator": "equal", "operand": true, "match_all": true },
                { "key": "following_text", "operator": "regex_contains", "operand": "^\"", "match_all": true },
                { "key": "selector", "operator": "not_equal", "operand": "punctuation.definition.string.begin", "match_all": true },
                { "key": "eol_selector", "operator": "not_equal", "operand": "string.quoted.double - punctuation.definition.string.end", "match_all": true },
            ]
        },

        Produces:
        ---------
        ReportKeyBinding(source=Default/Default (Windows).sublime-keymap
          { ['"'], move(({'by': 'characters', 'forward': true}))
            "context": [
              { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": true }
              { "key": "selection_empty"           , "operator": "equal"         , "operand": true, "match_all": true }
              { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": true }
              { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": true }
              { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": true }
            ]
          })

        or if there is no "context" entry:

        ReportKeyBinding pkg=Default { ['right'], move({'by': 'characters', 'forward': true}) }>

        """
        binding_str = self.formatted(1)
        return f'{self.__class__.__name__}( source: {self._source}\n{binding_str})'

    def args_rst(self) -> str:
        result = self.args_json()

        if result:
            if 'res://' in result:
                # Wrap the whole thing in a literal.
                result = '``' + result + '``'
            else:
                result = rst_escaped(result)

        return result

    # def main_key_names(self) -> list[str]:
    #     return self._main_key_names

    # def main_key_name_rst_escaped(self) -> str:
    #     return rst_escaped(self._main_key_names[0])

    # def leading_key_name(self) -> str:
    #     if self._main_key_names:
    #         result = self._main_key_names[0]
    #     else:
    #         result = '?'

    #     return result

    def modifier_codes(self) -> list[int]:
        return self._modifier_codes

    def leading_modifier_code(self) -> int:
        if self._modifier_codes:
            result = self._modifier_codes[0]
        else:
            result = 0

        return result

    def keypresses_human_friendly_list(self) -> list[str]:
        """ e.g. Alt-Shift-R """
        result = []
        for keypress in self.keypresses:
            result.append(keypress.human_friendly_repr())

        return result

    def keypresses_human_friendly_rst_list(self) -> list[str]:
        result = []
        hf_list = self.keypresses_human_friendly_list()
        for hf_str in hf_list:
            result.append(f':kbd:`{hf_str}`')

        return result

    def command_as_function_rst(self) -> str:
        result = self.command_as_function_repr()

        if 'res://' in result:
            # Wrap the whole thing in a literal.
            result = '``' + result + '``'

        return result

