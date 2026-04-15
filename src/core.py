r"""
KeyBindingReport
****************

Definitions
===========

key modifier code
    integer value defining the possible combination of the modifier keys
    [Ctrl], [Alt] and [Shift] that were part of a keypress.  The
    ``ModifierKeyBits`` class provides bits which are bitwise-OR-ed together
    to form the integer value [0-7].  See "Design Factor" below for
    the reason this is needed.

keypress
    a single keystroke with a possible key modifier.

    Each keypress has a "main" key, which is in the "Key Names" list below.
    Note that since these are KEYS and not characters, so shifted characters
    like ':' are not in the list, as they are represented as [Shift] + ';'.

    Examples:  "ctrl+p", "ctrl+shift+p", "f5", "alt+f5".

keypress sequence
    A keypress sequence is when a Command is bound to a sequence of more than one
    keypress.  Example:

    - ["ctrl+k", "ctrl+b"] (show/hide Side Bar),
    - ["ctrl+k", "ctrl+u"] (upper-case selected text or word if no text is selected),
    - ["ctrl+k", "ctrl+l"] (lower-case selected text or word if no text is selected).

keys (plural)
    List[str]:  corresponds with the ``.sublime-keymap`` entries called
    "keys", each of which has a value which is itself a lists of 1 or more
    keypresses.  They must contain at least 1 string.  Examples:

    - ["ctrl+shift+p"]
    - ["ctrl+k", "ctrl+u"]
    - ["up"]
    - ["enter"]

keys_list
    List[List[str]]:  a list of "keys" as defined above.  They can
    contain 0 or more "keys", and may even contain duplicate keypresses/
    keypress sequences since they may be supplied by a user calling
    ``view.run_command("key_binding_report", custom_args).  Examples:

    - []
    - [["ctrl+shift+p"]]
    - [["ctrl+k", "ctrl+u"]]
    - [["up"], ["f5"], ["shift+f5"], ["ctrl+shift+f5"], ["ctrl+k", "ctrl+u"]]
    - [["enter"], ["ctrl+k", "ctrl+u"], ["ctrl+k", "ctrl+u"]]

key ID
    index into the ``core.all_key_names`` list identifying a particular keyboard key.

encoded keypress
    an integer whose bits are the bitwise-OR-ed combination of the key ID
    and the key modifier value:

        encoded_keypress = (i << 4) | modifier_value

    where:

    - ``i`` is the key ID (index into the ``core.all_key_names`` list), and
    - ``modifier_value`` is comprised of OR-ed bits from ``ModifierKeyBits``.

    While the key modifier code only needs 3 bits, 4 bits is used so its parts can
    easily be seen in a hexadecimal representation of the integer result.

JSON key-binding object
    a Python dictionary representation of a key-binding object from any of
    the .sublime-keymap files.

    Example of JSON key-binding object:

    .. code-block:: json

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

KeyBinding object
    an instance of the ``KeyBinding`` class, containing the JSON key-binding
    object from a ``.sublime-keymap`` file (defining the binding of an individual
    keypress/keypress sequence), plus some additional data:  the name of the
    Package and ``.sublime-keymap`` file it came from.

    Note that during instantiation of a new ``KeyBinding`` object, the
    JSON key-binding object's "keys" value is converted from a list to
    a tuple for ease of use as dictionary keys and in sets.

-----


Design Factor
=============

In the ``Default`` Package and in most other places where official ``.sublime-keymap``
files can be found, the "keys" entry (e.g. ``"keys": ["alt+shift+up"]``) in each
JSON key-binding object has a specific order of modifier-key strings among the '+'
characters, and it is always in this sequence:

- ctrl
- alt
- shift

However, Sublime |nbsp| Text allows users to include key overrides in
``.sublime-keymap`` files that do not follow this pattern (e.g. "shift+alt+8"
instead of "alt+shift+8"), so when we read in JSON key-binding objects from
``.sublime-keymap`` files, we cannot rely on this sequence since some of
them are user override files.  Therefore, we use the ``ModifierKeyBits``
class to generate a numeric value in the range[0-7] which gives a
consistent unique integer value which can be used in different ways as
needed.  Such values will be created something like this:

.. code-block:: py

    key_modifier_code = 0

    modifier_str = 'shift+'
    if modifier_str in keypress_str:
        key_modifier_code |= ModifierKeyBits.SHIFT
        keypress_str = keypress_str.replace(modifier_str, '')

    modifier_str = 'ctrl+'
    if modifier_str in keypress_str:
        key_modifier_code |= ModifierKeyBits.CTRL
        keypress_str = keypress_str.replace(modifier_str, '')

    modifier_str = 'alt+'
    if modifier_str in keypress_str:
        key_modifier_code |= ModifierKeyBits.ALT
        keypress_str = keypress_str.replace(modifier_str, '')

    main_key = keypress_str


Key-Binding Data Structures
===========================

To generate the Key-Binding Report, the preparation to do that involves
building several data structures from the contents of the installed
``.sublime-keymap`` files.  One of these structures is similar to what
Sublime Text probably uses internally to select the appropriate key
binding based on the caret's current scope.

In this design we are NOT building a "big master database" from which
lookups can be done, but instead are using input arguments from the
caller to limit what data is gathered.  Then the report is generated
from ALL the data thus gathered.  Since each report can be different,
the data is gathered afresh for each report.

Here are the data structures used.


By Main-Key Dictionary
----------------------

This dictionary is for key bindings that involve only one keypress.

KEYS:

Its keys are the key names of the main key in each keypress.
See key names below.  Example:  "up".

VALUES:

Each entry's VALUE is a list of exactly 8 possible key modifiers, where
the ``ModifierKeyBits`` class combinations of modifier keys forms the index
of which list item, as described above under "Design Factor".

Key:
    A = Alt
    C = Ctrl
    S = Shift
    i = Index

+----------+-+-+-+---+
| Key Name |A|C|S| i |
+==========+=+=+=+===+
| up       | | | | 0 |
| up       | | |x| 1 |
| up       | |x| | 2 |
| up       | |x|x| 3 |
| up       |x| | | 4 |
| up       |x| |x| 5 |
| up       |x|x| | 6 |
| up       |x|x|x| 7 |
+----------+-+-+-+---+

Note:  this modifier-key order is for the report.  This differs from the
conventional modifier-key order of strings found in .sublime-keymap files,
which is "ctrl", "alt", then "shift", in that order.  Note that this is a
*convention*, not a requirement of Sublime Text, which permits users to
provide keymap overrides that use a different order (so long as the main
key is last).  The `ModifierKeyBits` class helps compute this index.

Each such list item then contains ``None`` or a list of ``KeyBinding``
objects for that particular keypress.  The order of that list is in
``.sublime-keymap`` file-loading order, and thus is similar to what
Sublime Text uses internally to select key bindings by doing a
reverse-sequence search on that list, until it finds a context that
matches the current scope (and other factors that may be specified
in the context conditions).

This also makes it possible to, to provide a "Which Binding?" report that
looks up keypresses in the same way Sublime Text does, and reports which
key bindings were selected from a list of input keypresses or keypress
sequences, including the name of the Package, and even the file that
contains it.

.. code-block:: text

    by_main_key_dict
        "a": [
                None,   # binding list for unmodified 'a' key
                None,   # binding list for [Shift-a]
                [...],  # binding list for [Ctrl-a]
                [...],  # binding list for [Ctrl-Shift-a]
                None,   # binding list for [Alt-a]
                None,   # binding list for [Alt-Shift-a]
                None,   # binding list for [Alt-Ctrl-a]
                None,   # binding list for [Alt-Ctrl-Shift-a]
            ]


By Keypress Sequence Dictionary
-------------------------------

This dictionary is for key bindings that involve more than one keypress.
This dictionary is used in combination with ``by_main_key_dict`` so that
when a keypress is mapped in both places (as is the case with [Ctrl-T]
when the ``sublime-rst-completion`` Package is installed), if the context
is such that the keypress in THIS dictionary may also apply, the keypress
has to be repeated in order to select the Key-Binding from plain
``by_main_key_dict``, whereas if the additional keypresses are found in
sequence in this dictionary, that Key-Binding is chosen instead.  If a
keypress is encountered not contained in a known key sequence in this
dictionary, then the whole key sequence is abandoned, the key sequence
state machine is reset, and no Key Binding is selected.

This capability is needed in order to report what key binding was
selected for those type of keypress sequences.  Also, the user can
request a report that includes keypress sequences, so this is the
source dictionary for those reports.

KEYS:

The key for each entry is the tuple of keypresses that make it up.
(Lists cannot be dictionary keys because they are mutable.)
Example:  ``("ctrl+k", "ctrl+up")``.

VALUES:

Each entry's VALUE is a list of Key-Binding objects (defined above)
associated with the keypress sequence in the key.  The order of that list
is in ``.sublime-keymap`` file-loading order, and thus is similar to what
Sublime Text uses internally to map keystrokes by doing a reverse-sequence
search on that list, until it finds a context that matches the current
context.

This also makes it possible to, to provide a "Which Binding?" report that
looks up keypresses in the same way Sublime Text does, and reports which
key bindings were selected from a list of input keypresses or keypress
sequences, including the name of the Package, and even the file that
contains it.

.. code-block:: text

    by_key_seq_dict
        ("ctrl+k", "ctrl+up"):
            [
                Key-Binding object,
                Key-Binding object,
                Key-Binding object,
                ...
            ]


Key Names
=========

Key names are specified either by the (non-shifted) character printed on
the key, or a key name:

.. code-block:: text

    a   n   0   f1    ,   up           keypad0
    b   o   1   f2    .   down         keypad1
    c   p   2   f3    \   left         keypad2
    d   q   3   f4    /   right        keypad3
    e   r   4   f5    ;   insert       keypad4
    f   s   5   f6    '   delete       keypad5
    g   t   6   f7    `   home         keypad6
    h   u   7   f8    +   end          keypad7
    i   v   8   f9    -   pageup       keypad8
    j   w   9   f10   =   pagedown     keypad9
    k   x       f11   [   backspace    keypad_period
    l   y       f12   ]   tab          keypad_divide
    m   z       f13       enter        keypad_multiply
                f14       pause        keypad_minus
                f15       escape       keypad_plus
                f16       space        keypad_enter
                f17       break        clear
                f18       context_menu
                f19
                f20
    \___/   ^    ^    ^     ^            ^
      |     |    |    |     |            |
      |     |    |    |     |            +-- KEYPAD_KEYS
      |     |    |    |     +-- NAMED_KEYS
      |     |    |    +-- SYMBOL_KEYS
      |     |    +-- F_KEYS
      |     +-- NUMBER_KEYS
      +-- LETTER_KEYS

    The above enumerator names are from the ``KeyGroup`` class.
    Note that identify lists of key names that are mutually exclusive.


Ways to Limit Output
====================

See ``KeyBindingReportCommand`` docstring for details.

"""

from datetime import datetime
from typing import List, Tuple, Dict, Set, Optional
import re
import os
import sys
import sublime
import sublime_plugin
from enum import IntEnum, IntFlag
from ..lib.ascii_table import Format, Generator
from ..lib.debug import DebugBits, is_debugging, set_debugging_bits
from ..lib import utils
from ..keybindingreport import package_name


# =========================================================================
# Configuration
# =========================================================================

# Use name of parent directory as `package_name`.
_cfg_pkg_settings_file                   = package_name + '.sublime-settings'

# Track on-settings-changed listener.
_cfg_on_settings_chgd_listener_id        = '_kbr_settings_changed_tag'

# Package Settings Names (most are used multiple times throughout this Plugin)
_cfg_stg_name__debugging                 = 'debugging'


# =========================================================================
# Package Settings
# =========================================================================

def kbr_setting(setting_name: str):
    """
    Get a setting from a cached settings object.
    This function expects the following objects to already exist:

    - ``kbr_setting.obj``      a ``sublime.Settings`` object (looks like a dictionary)
    - ``kbr_setting.default``  a dictionary object with named default values

    :param setting_name:  name of setting whose value will be returned
    """
    if not hasattr(kbr_setting, 'default') or kbr_setting.default is None:
        raise AssertionError('`kbr_setting.default` must exist before calling `kbr_setting()`.')
    if not hasattr(kbr_setting, 'obj') or kbr_setting.obj is None:
        raise AssertionError('`kbr_setting.obj` must exist before calling `kbr_setting()`.')
    default = kbr_setting.default.get(setting_name, None)
    return kbr_setting.obj.get(setting_name, default)


# =========================================================================
# Load default settings once.
# =========================================================================

kbr_setting.default = {
    _cfg_stg_name__debugging: False
}


# =========================================================================
# Package-Wide Classes
# =========================================================================

class KeyGroup(IntEnum):
    """ Non-negative values index into ``key_name_groups``. """
    ALL            = -2  # Equivalent to specifying all groups >= 0.
    KEY_SEQUENCES  = -1  # Multiple-keypress sequences, e.g. ["ctrl+k", "ctrl+u"]

    LETTER_KEYS    =  0  # \
    NUMBER_KEYS    =  1  #  \
    F_KEYS         =  2  #   \__ These index into ``key_name_groups``.
    SYMBOL_KEYS    =  3  #   /
    NAMED_KEYS     =  4  #  /
    KEYPAD_KEYS    =  5  # /


class ModifierKeyBits(IntFlag):
    SHIFT         = 0b001
    CTRL          = 0b010
    ALT           = 0b100

    NONE          = 0b000
    ALL           = 0b111
    ANY           = 0b111


class FlagBits(IntFlag):
    SHOW_UNBOUND_KEY_COMBINATIONS = 0b00000001  #   1
    SHOW_PACKAGE_NAME             = 0b00000010  #   2
    ADD_COMMENTS_COLUMN           = 0b00000100  #   4
    INCLUDE_UNTRANSLATED_CONTEXTS = 0b00001000  #   8
    INCLUDE_ENGLISH_CONTEXTS      = 0b00010000  #  16

    NONE                          = 0b00000000  #   0
    ALL                           = 0b11111111  # 255
    ANY                           = 0b11111111  # 255


class KeyBinding():
    """
    Representation of a Key-Binding JSON object from a ``.sublime-keymap``
    file, plus some additional data needed for reporting, e.g. what Package
    the binding is from.
    """
    def __init__(self, json_binding_obj: dict, pkg_name: str, file_name: str):
        self.json_binding = json_binding_obj
        self.pkg_name     = pkg_name
        self.file_name    = file_name
        # Ensure keys is a tuple to simplify comparisons and use in
        # dictionary keys and set.
        keys_list = self.json_binding['keys']
        keys_tuple = tuple(keys_list)
        self.json_binding['keys'] = keys_tuple

    def __repr__(self):
        pkg = self.pkg_name
        keys = repr(self.json_binding['keys'])
        cmd = self.json_binding['command']
        args_dict = {}
        context = []

        if 'args' in self.json_binding:
            args_dict = repr(self.json_binding['args'])
        if 'context' in self.json_binding:
            context = repr(self.json_binding['context'])

        result = f'<pkg={pkg} {keys}: {cmd}'

        if args_dict:
            result += f'({args_dict})'
        else:
            result += '()'

        if context:
            result += f', {context=}'

        result += '>'
        return result

    def keypress_count(self) -> int:
        """
        Number of keypresses in binding.
        """
        return len(self.json_binding['keys'])

    def keys(self) -> tuple:
        return self.json_binding['keys']

    def command(self) -> str:
        return self.json_binding['command']

    def args(self) -> Optional[dict]:
        result = None

        if 'args' in self.json_binding:
            result = self.json_binding['args']

        return result

    def context(self) -> Optional[list]:
        result = None

        if 'context' in self.json_binding:
            result = self.json_binding['context']

        return result

    def extracted_json_parts(self) -> Tuple[Tuple[str], str, dict, List[dict]]:
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
        json_binding = self.json_binding
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

    def package_name(self) -> str:
        return self.pkg_name

    def keymap_file_name(self) -> str:
        return self.file_name


# =========================================================================
# Constants (can be assigned/generated once on Package load)
# =========================================================================

platform_name = {
    'osx': 'OSX',
    'windows': 'Windows',
    'linux': 'Linux',
}[sublime.platform()]
platform_name_w_parens = '(' + platform_name + ')'

# Regex to extract package name from resource path.
# Example of input:  'Packages/ScopeView/Default (Windows).sublime-keymap'
pkg_name_from_resource_path_re = re.compile(r'^Packages/([^/]+)/(.*)$')
platform_name_from_file_name_re = re.compile(r'^Default \((.*)\)\.sublime-keymap$')

# Key Name Groups, indexed by class ``KeyGroup``.
key_name_groups = [
    # LETTER_KEYS == 0
    ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'],
    # NUMBER_KEYS == 1
    ['0','1','2','3','4','5','6','7','8','9'],
    # F_KEYS      == 2
    ['f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12','f13','f14','f15','f16','f17','f18','f19','f20'],
    # SYMBOL_KEYS == 3
    [',','.','\\','/',';',"'",'`','+','-','=','[',']',
            '"', '(', ')', '[', ']', '{', '}'],
            # These last 7 are added because these "bare" keypresses (i.e.
            # having no ctrl/alt/shift key modifiers) are bound in the
            # Default keymap, so these need to be here for them to be included.
            #
            # These "bare" keys are also bind-able, but this is not recommended:
            # '`', '~', '!', '@', '#', '$', '%', '^', '&',
            # '*', '_', '+', '|', ':', '"', '<', '>', '?'.
    # NAMED_KEYS  == 4
    ['up','down','left','right','insert','delete','home','end','pageup','pagedown','backspace','tab','enter','pause','escape','space','break','context_menu'],
    # KEYPAD_KEYS == 5
    ['keypad0','keypad1','keypad2','keypad3','keypad4','keypad5','keypad6','keypad7','keypad8','keypad9','keypad_period','keypad_divide','keypad_multiply','keypad_minus','keypad_plus','keypad_enter','clear'],
]

# Generate ``all_key_names`` from ``key_name_groups``.
count = 0

for grp in key_name_groups:
    count += len(grp)

# Pre-allocate array instead of 103 ``append()`` calls (inefficient).
all_key_names = [None] * count
i = 0

for grp in key_name_groups:
    for key_name in grp:
        all_key_names[i] = key_name
        i += 1

# Generate ``key_index_by_key_name_dict`` from ``all_key_names``.
# This dictionary's values index into ``all_key_names``, while also giving
# each key name an integer value.  This enables us to produce a unique
# integer value for each possible key with all 8 modifier possibilities
# with something like this:
#
#     encoded_keypress = (i << 4) | modifier_value
#
# where ``modifier_value`` is comprised of OR-ed bits from ModifierKeyBits.
key_index_by_key_name_dict = {}

for i, key_name in enumerate(all_key_names):
    key_index_by_key_name_dict[key_name] = i

# Create 2 lookup data structures.
gdictByMainKey = {}
gdictByKeySquence = {}

# Clean up.
del i, count, grp, key_name


# =========================================================================
# Data
# =========================================================================

_debugging_filtering_stage_i = False
_debugging_filtering_stage_ii = False
_debugging_scope = False
_debugging_building_main_key_dict = False
_debugging_building_key_seq_dict = False


def _update_debugging_flags():
    """
    Debugging is done this way (with global variables) so that we don't
    have to call ``is_debugging()`` or pass debugging variables inside
    a 6-deep call-stack while processing a 3-deep loop.  Both are
    ``is_debugging()`` and loading up the stack with arguments that many
    considered unnecessary CPU load, so it is done here ONCE and accessed
    from within functions used in this loop below to avoid that overhead.

    + for each .sublime-keymap file...
      + for each JSON key binding...
        + for each condition in context...
    """
    global _debugging_filtering_stage_i
    global _debugging_filtering_stage_ii
    global _debugging_scope
    global _debugging_building_main_key_dict
    global _debugging_building_key_seq_dict
    _debugging_filtering_stage_i      = is_debugging(DebugBits.FILTERING_STAGE_I)
    _debugging_filtering_stage_ii     = is_debugging(DebugBits.FILTERING_STAGE_II)
    _debugging_scope                  = is_debugging(DebugBits.FILTERING_ON_SCOPE)
    _debugging_building_main_key_dict = is_debugging(DebugBits.BUILDING_MAIN_KEY_DICT)
    _debugging_building_key_seq_dict  = is_debugging(DebugBits.BUILDING_KEY_SEQ_DICT)


# =========================================================================
# Utilities
# =========================================================================

def timestamp() -> str:
    """ Universal timestamp; used in some Package debug output. """
    now = datetime.now()
    fmt = '%Y-%m-%d %H:%M'
    return now.strftime(fmt)


def is_list_tuple_or_set(obj) -> bool:
    """ Is passed class a list, set or tuple? """
    T = type(obj)
    return (( T == list or T == tuple or T == set ))


def arg_type_error_message(arg, arg_name: str, required_type: str, after_matter: str = ''):
    c = required_type[0]
    article = 'a'
    if c in 'aeiou':
        article = 'an'

    return f'`{arg_name}` arg must be {article} {required_type}. Instead got {type(arg)}.{after_matter}'


# =========================================================================
# Function Definitions
# =========================================================================

def main_key_and_modifier_code(keypress_str: str) -> Tuple[str, int]:
    """ Extract main key name and key-modifier code from ``keypress_str``. """
    lsWorkingKeypress = keypress_str

    # Here we know gdictByMainKey[main_key_name] exists.
    key_modifier_code = 0

    modifier_str = 'shift+'
    if modifier_str in lsWorkingKeypress:
        key_modifier_code |= ModifierKeyBits.SHIFT
        lsWorkingKeypress = lsWorkingKeypress.replace(modifier_str, '')

    modifier_str = 'ctrl+'
    if modifier_str in lsWorkingKeypress:
        key_modifier_code |= ModifierKeyBits.CTRL
        lsWorkingKeypress = lsWorkingKeypress.replace(modifier_str, '')

    modifier_str = 'alt+'
    if modifier_str in lsWorkingKeypress:
        key_modifier_code |= ModifierKeyBits.ALT
        lsWorkingKeypress = lsWorkingKeypress.replace(modifier_str, '')

    main_key_name = lsWorkingKeypress

    return main_key_name, key_modifier_code


def encoded_keypress_from_components(main_key_name: str, key_modifier_code: int):
    i = key_index_by_key_name_dict[main_key_name]
    return (i << 4) | key_modifier_code


def encoded_keypress(keypress_str: str) -> int:
    """ `keypress_str` encoded as ((i << 4) | modifier_value) """
    kn, mod_val = main_key_and_modifier_code(keypress_str)
    return encoded_keypress_from_components(kn, mod_val)


def _add_binding_to_main_key_dict(binding: KeyBinding, key_name: str, key_mod_code: int):
    """
    by_main_key_dict
        "a": [
                None,   # binding list for unmodified 'a' key
                None,   # binding list for [Shift-a]
                [...],  # binding list for [Ctrl-a]
                [...],  # binding list for [Ctrl-Shift-a]
                None,   # binding list for [Alt-a]
                None,   # binding list for [Alt-Shift-a]
                None,   # binding list for [Alt-Ctrl-a]
                None,   # binding list for [Alt-Ctrl-Shift-a]
            ]
    """
    global gdictByMainKey

    if _debugging_building_main_key_dict:
        print('In _add_binding_to_main_key_dict()...')
        print(f'{key_name=}')
        print(f'{key_mod_code=}')

    if binding.keypress_count() != 1:
        raise AssertionError(f'Number of elements in `keys` expected 1, got {binding.keypress_count()}!')
    if key_name not in gdictByMainKey:
        raise AssertionError(f'  ERROR!  Found key name [{key_name}] not in gdictByMainKey.')

    # Here we know gdictByMainKey[key_name] exists.
    by_main_key_item = gdictByMainKey[key_name]
    key_binding_list = by_main_key_item[key_mod_code]

    if key_binding_list is None:
        # Lazy list creation
        by_main_key_item[key_mod_code] = []
        key_binding_list = by_main_key_item[key_mod_code]

    key_binding_list.append(binding)
    # if _debugging_building_main_key_dict:
    #     print(f'  Added [{keypress_str}] binding to item [{key_mod_code}].')


def _add_binding_to_key_seq_dict(binding: KeyBinding):
    """
    by_key_seq_dict
        ("ctrl+k", "ctrl+up"):
            [
                Key-Binding object,
                Key-Binding object,
                Key-Binding object,
                ...
            ]
    """
    assert binding.keypress_count() > 1, f'Number of elements in `keys` expected > 1, got {binding.keypress_count()}!'
    if _debugging_building_key_seq_dict:
        print('In _add_binding_to_key_seq_dict()...')

    global gdictByKeySquence
    keys_tuple = binding.keys()

    if keys_tuple not in gdictByKeySquence:
        # Lazy creation.
        gdictByKeySquence[keys_tuple] = []

    binding_list = gdictByKeySquence[keys_tuple]
    binding_list.append(binding)
    if _debugging_building_key_seq_dict:
        print(f'  Added binding for {keys_tuple}.')


def _build_empty_main_key_dict():
    """
    ``by_main_key_dict`` has a structure that will only ever be partially
    populated, but must be fully represented with its empty parts.

    by_main_key_dict
        "a": [
                None,   # binding list for unmodified 'a' key
                None,   # binding list for [Shift-a]
                [...],  # binding list for [Ctrl-a]
                [...],  # binding list for [Ctrl-Shift-a]
                None,   # binding list for [Alt-a]
                None,   # binding list for [Alt-Shift-a]
                None,   # binding list for [Alt-Ctrl-a]
                None,   # binding list for [Alt-Ctrl-Shift-a]
            ]
    """
    if _debugging_building_main_key_dict:
        print('In _build_empty_main_key_dict()')

    global gdictByMainKey
    gdictByMainKey = {}

    for key_name in all_key_names:
        empty_list = [None] * 8
        gdictByMainKey[key_name] = empty_list

    # if _debugging_building_main_key_dict:
    #     print('  Empty by-main-key dict:')
    #     print(repr(gdictByMainKey))


def _build_empty_key_seq_dict():
    """
    ``by_key_seq_dict`` is valid just being an empty dictionary as it
    is populated when the keypress sequences are encountered.

    by_key_seq_dict
        ("ctrl+k", "ctrl+up"):
            [
                Key-Binding object,
                Key-Binding object,
                Key-Binding object,
                ...
            ]
    """
    if _debugging_building_key_seq_dict:
        print('In _build_empty_key_seq_dict()')

    global gdictByKeySquence
    gdictByKeySquence = {}


def _condition_test(
        view          : sublime.View,
        scope         : str,
        keypress_tuple: Tuple[str],
        condition     : dict
        ):
    """
    :param view:            Current View (used to test if key context is applicable)
    :param scope:           Scope string of first caret in View (if needed)
    :param keypress_tuple:  Tuple containing keypress/keypress sequence
    :param condition:       Single condition dictionary from key-binding context.
    """
    result = False

    if not result:
        if _debugging_scope:
            print(f'  Excluding {keypress_tuple_bep} because context condition failed:\n    {condition}')

    return result


def _contex_applies(
        view          : sublime.View,
        scope         : str,
        keypress_tuple: Tuple[str],
        context       : List[dict]
        ):
    """
    :param view:            Current View (used to test if key context is applicable)
    :param scope:           Scope string of first caret in View (if needed)
    :param keypress_tuple:  Tuple containing keypress/keypress sequence
    :param context:         Context entry from key-binding
    """
    result = True

    # Do all conditions pass?
    all_conditions_passed = True
    for condition in context:
        if not _condition_test(view, scope, keypress_tuple, condition):
            all_conditions_passed = False
            break

    if not all_conditions_passed:
        if _debugging_scope:
            print(f'  Excluding {keypress_tuple_bep} because context does not apply.')

    return result


def _conditionally_add_bindings_from_keymap(
        view                    : sublime.View,
        scope                   : str,
        path                    : str,
        pkg_name                : str,
        file_name               : str,
        accepted_key_name_set   : Optional[Set[str]],
        keys_set                : Optional[Set[Tuple[str]]],
        accept_all_key_sequences: bool,
        limit_to_scope          : bool
        ):
    """
    Add key bindings from ``path``, limited by:

    - accepted_key_name_set   : Optional[Set[str]],
    - keys_set                : Optional[Set[Tuple[str]]],
    - limit_to_scope          : bool,
    - accept_all_key_sequences: bool


    :param view:            Current View (used to test if key context is applicable)
    :param scope:           Scope string of first caret in View (if needed)
    :param path:            Packages path to .sublime-keymap file
    :param pkg_name:        Name of package (extracted by caller and used here)
    :param file_name:       .sublime-keymap file name without path.

    :param accepted_key_name_set:
                            Optional:  Set against which to compare key
                            names when keypress count == 1, to accept or
                            reject key bindings being read; ``None`` == no
                            limits on key bindings.

    :param keys_set:        Optional:  Set of keypress tuples against which
                            to compare individual JSON key binding objects.
                            If the keypress tuple is a match, then it is
                            included in the input data. ``None`` == no
                            specific keypress/keypress sequences are added.

    :param limit_to_scope:  Exclude key bindings that don't apply to current
                            scope?

    :param accept_all_key_sequences:
                            Whether to accept all keypress sequences
                            (i.e. JSON key-binding "keys" list values that
                            have more than one keypress string in them).
    """
    if _debugging_filtering_stage_ii:
        print(f'In _conditionally_add_bindings_from_keymap()')
        print(f'  {path=}')
        print(f'  {accepted_key_name_set=}')
        print(f'  {keys_set=}')
        print(f'  {accept_all_key_sequences=}')
        print(f'  {limit_to_scope=}')

    keymap_resource_str = sublime.load_resource(path)
    json_key_bindings = sublime.decode_value(keymap_resource_str)

    for json_binding in json_key_bindings:
        # First, look for reasons to exclude key binding.
        keypress_tuple_bep = tuple(json_binding['keys'])
        keypress_count_bep = len(keypress_tuple_bep)

        # Exclude key sequences (keypress_count_bep > 1)?
        if keypress_count_bep > 1:
            # Is a key sequence.
            # Exclude if not accept_all_key_sequences and not in ``keys_set``
            if not accept_all_key_sequences:
                if keys_set:
                    # Exclude if not in ``keys_set``.
                    if keypress_tuple_bep not in keys_set:
                        if _debugging_filtering_stage_ii:
                            print(f'  Excluding {keypress_tuple_bep} because:\n'
                                    f'    - KEY_SEQUENCES was not in `key_groups`,\n'
                                    f'    - that keypress sequence was not in `keys_list`.'
                                    )
                        continue
                else:
                    # ``keys_set`` not present, exclude.
                    if _debugging_filtering_stage_ii:
                        print(f'  Excluding {keypress_tuple_bep} because:\n'
                                f'    - KEY_SEQUENCES was not in `key_groups`, and\n'
                                f'    - that keypress sequence was not in `keys_list`.'
                                )
                    continue
        elif keypress_count_bep == 0:
            # Binding encountered that has no "keys" entry!
            # This is an error the user needs to fix.
            print(f'{package_name} Error:  Cannot include JSON key binding with empty "keys" entry!\n'
                    f'  {keypress_tuple_bep}'
                    )
            continue
        else:
            # Single keypress.  Exclude if neither in
            # ``accepted_key_name_set`` nor ``keys_set``.
            is_in_keys_set = ((
                        keys_set is not None
                    and len(keys_set) > 0
                    and keypress_tuple_bep in keys_set
                    ))

            if not is_in_keys_set:
                if accepted_key_name_set:
                    keypress_str = keypress_tuple_bep[0]
                    key_name, mod_val = main_key_and_modifier_code(keypress_str)

                    if key_name not in accepted_key_name_set:
                        # This should be excluded UNLESS, but ``keys_set`` is
                        # additive, so if ``key_set`` was provided AND the
                        # keypress is in it, then the caller specifically
                        # requested that keypress, so it should be included.
                        if _debugging_filtering_stage_ii:
                            print(f'  Excluding {keypress_tuple_bep} because:\n'
                                    f'    - that key_name was neither in `key_names` nor `key_groups`, and\n'
                                    f'    - that keypress was not in `keys_list`.'
                                    )
                        continue
                else:
                    # Is neither in ``key_set`` nor ``accepted_key_name_set``.
                    if _debugging_filtering_stage_ii:
                        print(f'  Excluding {keypress_tuple_bep} because:\n'
                                f'    - that key_name was neither in `key_names` nor `key_groups`, and\n'
                                f'    - that keypress was not in `keys_list`.'
                                )
                    continue

        # Exclude if caller requested a limiting scope, and the
        # scope doesn't apply to the current scope.
        if limit_to_scope and 'context' in json_binding:
            # Do context conditions ALL fit limiting scope?
            if not _contex_applies(
                    view,
                    scope,
                    keypress_tuple_bep,
                    json_binding['context']
                    ):
                continue

        # When execution arrives here, none of the reasons to
        # exclude the key binding applied:  it's okay to add.
        binding = KeyBinding(json_binding, pkg_name, file_name)
        _add_binding_to_key_seq_dict(binding)


def build_report_data(
        packages                 : Optional[Set[str]],
        accepted_key_name_set    : Optional[Set[str]],
        keys_set                 : Optional[Set[Tuple[str]]],
        limit_to_scope           : bool,
        accept_all_key_sequences : bool
        ):
    """
    Build report data required by the report dictated by the 3 arguments.
    This function only gathers information needed for the report.

    Output:
        global gdictByMainKey
        global gdictByKeySquence

    Each of the parameters are part of enabling JSON key binding objects
    to be rejected quickly, i.e. NOT included in the input data, so that
    what is left in the INPUT data is exactly what the user requested.


    :param packages:        Optional:  Set of packages to limit data to;
                            ``None`` == no limits on packages.

    :param accepted_key_name_set:
                            Optional:  Set against which to compare key
                            names when keypress count == 1, to accept or
                            reject key bindings being read; ``None`` == no
                            limits on key bindings.

    :param keys_set:        Optional:  Set of keypress tuples against which
                            to compare individual JSON key binding objects.
                            If the keypress tuple is a match, then it is
                            included in the input data. ``None`` == no
                            specific keypress/keypress sequences are added.

    :param limit_to_scope:  Exclude key bindings that don't apply to current
                            scope?

    :param accept_all_key_sequences:
                            Whether to accept all keypress sequences
                            (i.e. JSON key-binding "keys" list values that
                            have more than one keypress string in them).

    :return:  None


    Algorithm
    ---------

    If ``packages`` specified and not empty, `.sublime-keymap` files
    not in those Packages are not included in the input data.

    Note:

        When there are platform-dependent keymap files in a package, e.g.

        - Default (OSX).sublime-keymap
        - Default (Linux).sublime-keymap
        - Default (Windows).sublime-keymap

        only the keymap applicable to the current platform is used as input.


    """
    _update_debugging_flags()

    if _debugging_filtering_stage_i:
        print(f'In build_report_data()')
        print(f'  {packages=}')
        print(f'  {accepted_key_name_set=}')
        print(f'  {keys_set=}')
        print(f'  {limit_to_scope=}')
        print(f'  {accept_all_key_sequences=}')

    # Start fresh.
    _build_empty_main_key_dict()
    _build_empty_key_seq_dict()

    # Compute view and scope ONCE before we enter loop.
    view = sublime.active_window().active_view()
    live_sel_rgn_list = view.sel()
    if len(live_sel_rgn_list) == 0 and limit_to_scope:
        print(
                f'  {package_name} Exception:\n'
                '    There were no carets in View when the `key_binding_report`\n'
                '    command was run and `limit_to_scope` == True.'
                )
        return

    # Use only first selection, and position of caret if any text is selected.
    sel_rgn = live_sel_rgn_list[0]
    scope = view.scope_name(sel_rgn.b)

    # Loop through list of .sublime-keymap files in keymap-load order.
    keymap_paths = sublime.find_resources('*.sublime-keymap')

    for path in keymap_paths:
        match = pkg_name_from_resource_path_re.search(path)
        if not match:
            raise AssertionError(f'  >>> ERROR >>> Resource path pattern not recognized!  [{path}]')
        pkg_name = match[1]
        file_name = match[2]

        # -----------------------------------------------------------------
        # If `packages` specified, exclude Packages not in list.
        # -----------------------------------------------------------------
        if packages and pkg_name not in packages:
            if _debugging_filtering_stage_i:
                print(f'  Excluding package:  [{pkg_name}].')
            continue

        if _debugging_filtering_stage_i:
            print(f'  Including package:  [{pkg_name}].')

        # -----------------------------------------------------------------
        # If platform-specific `.sublime-keymap` file, exclude if not
        # current platform.
        # -----------------------------------------------------------------
        if 'Default (' in file_name:
            # Is a platform-specific key binding.
            if platform_name_w_parens not in file_name:
                if _debugging_filtering_stage_i:
                    match = platform_name_from_file_name_re.search(file_name)
                    if match:
                        lsPlatformName = match[1]
                        print(f'  Not a platform match:  {lsPlatformName} != {platform_name}.')
                    else:
                        print(f'  Not a platform match:  {file_name}.')
                continue

        if _debugging_filtering_stage_i:
            print(f'  Using {file_name}.')

        # -----------------------------------------------------------------
        # ``.sublime-keymap`` file is accepted.  Next stage.
        # -----------------------------------------------------------------
        _conditionally_add_bindings_from_keymap(
                view,
                scope,
                path,
                pkg_name,
                file_name,
                accepted_key_name_set,
                keys_set,
                accept_all_key_sequences,
                limit_to_scope
                )


# =========================================================================
# Events
# =========================================================================

def _on_pkg_settings_chgd():
    """
    Take action after Package settings have changed.
    """
    # Load overridable Package settings.
    # `kbr_setting()` cannot be called until this is done, and
    # `is_debugging()` will return an incorrect value until this is done.
    kbr_setting.obj = sublime.load_settings(_cfg_pkg_settings_file)

    # Initialize debugging subsystem.
    temp = kbr_setting(_cfg_stg_name__debugging)
    set_debugging_bits(temp)
    debugging = is_debugging(DebugBits.SETTINGS_CHANGED_EVENT)
    if debugging:
        print(f'In _on_pkg_settings_chgd()')


def on_plugin_loaded():
    """
    Initialize plugin; called by Sublime Text after plugin is loaded.
    """
    # Prepare cached Package settings.
    # Anything that relies on Package settings will not work before
    # ``_on_pkg_settings_chgd()`` is called, since it is what loads
    # the Package settings.
    _on_pkg_settings_chgd()
    debugging = is_debugging(DebugBits.LOAD_UNLOAD)
    if debugging:
        print(f'In {__package__}.core.on_plugin_loaded()')

    # Establish event hook for "settings changed" event. This allows the user
    # to change the lists that partake in the content of the RegEx that detects
    # Comment Specifier strings, and have updated behavior immediately after
    # saving the changed configuration. Note:  Callback must be unloaded in
    # `plugin_unloaded()` to prevent a callback leak.
    kbr_setting.obj.add_on_change(_cfg_on_settings_chgd_listener_id, _on_pkg_settings_chgd)

    # Report.
    if debugging:
        print(f'{package_name}:  Initialized at {timestamp()}.')


def on_plugin_unloaded():
    if hasattr(kbr_setting, 'obj'):
        # That test is for when this Plugin is in a state where it generates
        # an exception upon attempting to be loaded by Sublime Text, then
        # the `obj` attribute may not exist.
        if kbr_setting.obj:
            kbr_setting.obj.clear_on_change(_cfg_on_settings_chgd_listener_id)

    if is_debugging(DebugBits.LOAD_UNLOAD):
        print(f'{package_name}:  Plugin unloaded at {timestamp()}')
