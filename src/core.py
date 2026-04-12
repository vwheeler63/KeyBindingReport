r"""
KeyBindingReport
****************

Definitions
===========

key modifier
    the possible combination of the [Ctrl], [Alt] and [Shift] modifier keys
    that were part of a key-press.  The ``ModifierKeyBit`` class provides
    bits which are OR-ed together to form this integer value [0-7].

key press
    a single keystroke with a possible key modifier.  It may be hyphenated
    when used as a compound noun.

    Each key-press has a "main" key, which is in the ``key_names`` list below.

key ID
    index into the ``key_names`` list identifying a particular keyboard key.

key-press ID
    an integer whose bits are the bitwise-OR-ed combination of the key ID
    and the key modifier value like this:

        keypress_id = (i << 3) | modifier_value

    where:

    - `i` is the key ID (index into the `key_names` list), and
    - `modifier_value` is comprised of OR-ed bits from ``ModifierKeyBit``.

key-press sequence
    A key-press sequence is when a Command is bound to a sequence of more than one
    key-press.  Example:

    - ["ctrl+k", "ctrl+b"] (show/hide Side Bar),
    - ["ctrl+k", "ctrl+u"] (upper-case selected text or word if no text is selected),
    - ["ctrl+k", "ctrl+l"] (lower-case selected text or word if no text is selected).

KeyBinding Object
    an instance of the ``KeyBinding`` class, containing the JSON Key-Binding
    object from a `.sublime-keymap` file (defining the binding of an individual
    key press), plus some additional data like the name of the Package it came
    from.  Example of JSON Key-Binding object:

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

-----
alt+up
Design Factor
=============

In the ``Default`` Package and in most other places where official ``.sublime-keymap``
files can be found, the "keys" entry (e.g. ``"keys": ["alt+shift+up"]``) in each
Key-Binding Object has a specific order of modifier-key strings among the '+'
characters, and it is always in this sequence:

- ctrl
- alt
- shift

However, Sublime |nbsp| Text allows users to include key overrides in
``.sublime-keymap`` files that do not follow this pattern, so when we read
in Key-Binding Objects from ``.sublime-keymap`` files, we cannot rely on
this sequence since some of them are user override files.  Therefore, we
use the ``ModifierKeyBit`` class to generate a numeric value in the range
[0-7] which gives a consistent unique integer value which can be used in
different ways as needed.  Such values will be created something like this:

.. code-block:: py

    key_modifier_index = 0

    modifier_str = 'shift+'
    if modifier_str in keypress_str:
        key_modifier_index |= ModifierKeyBit.SHIFT
        keypress_str = keypress_str.replace(modifier_str, '')

    modifier_str = 'ctrl+'
    if modifier_str in keypress_str:
        key_modifier_index |= ModifierKeyBit.CTRL
        keypress_str = keypress_str.replace(modifier_str, '')

    modifier_str = 'alt+'
    if modifier_str in keypress_str:
        key_modifier_index |= ModifierKeyBit.ALT
        keypress_str = keypress_str.replace(modifier_str, '')

    # Now ``keypress_str`` contains just the name of the main key.


Key-Binding Lookup Data Structures
==================================

To generate the Key-Binding Report, the preparation to do that involves
building several "lookup data structures" from the contents of the installed
``.sublime-keymap`` files.  One of these structures is similar to what
Sublime Text probably uses internally to map each key-press to the Command
it is bound to.

In this design we choose NOT to incur the overhead of getting notified when
any of the Package ``.sublime-keymap`` files change.  To do that we'd have to:

- load each as a settings object (there are 41 of them in a modest
  Sublime Text installation, so we can count on 50 or 60 in installations
  that have a lot of Packages installed);
- using each object thus loaded, establish an "on-change" event for it to
  catch when any overrides of those keymaps got updated.

Thus, we cannot simply build these dictionaries ONCE when the Package is
loaded, but rather need to build them on-the-fly when a report is needed.
This also reduces Sublime Text's start-up time a bit by not automatically
doing that build for installations that include this Package.

Here is what the data structures look like.


By Main-Key Dictionary
----------------------

This dictionary is for key bindings that involve only one key-press.

KEYS:

Its keys are the key names of the main key in each key press.
See key names below.  Example:  "up".

VALUES:

Each entry's VALUE is a list of exactly 8 possible key modifiers, where
the ``ModifierKeyBit`` class combinations of modifier keys forms the index
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

Each such list item then contains ``None`` or a list of ``KeyBinding``
objects for that particular key-press.  The order of that list is in
``.sublime-keymap`` file-loading order, and thus is similar to what
Sublime Text uses internally to map keystrokes by doing a reverse-sequence
search on that list, until it finds a context that matches the current
context.

This also makes it possible to, in a user-input box, ask the user to
identify a key press (with possible modifiers), and then compute what key
binding it would hit in that search, including the name of the Package that
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


By Key Sequence Dictionary
--------------------------

This dictionary is for key bindings that involve more than one key-press.
This dictionary is used in combination with ``by_main_key_dict`` so that when
a key-press is mapped in both places (as is the case with [Ctrl-T] when the
``sublime-rst-completion`` Package is installed), if the context is such
that the key-press in THIS dictionary may also apply, the key-press has to
be repeated in order to select the Key-Binding from plain ``by_main_key_dict``,
whereas if the additional key-presses are found in sequence in this
dictionary, that Key-Binding is chosen instead.  If a key-press is
encountered not contained in a known key sequence in this dictionary, then
the whole key sequence is abandoned, the key sequence state machine is
reset, and no Key Binding is selected.

KEYS:

The key for each entry is the tuple of key-presses that make it up.
(Lists cannot be dictionary keys because they are mutable.)
Example:  ``("ctrl+k", "ctrl+up")``.

VALUES:

Each entry's VALUE is a list of Key-Binding objects (defined above)
associated with the key-press sequence in the key.  The order of that list
is in ``.sublime-keymap`` file-loading order, and thus is similar to what
Sublime Text uses internally to map keystrokes by doing a reverse-sequence
search on that list, until it finds a context that matches the current
context.

This also makes it possible to, in a user-input box, ask for a key-press
sequence, and tell the user exactly what key binding it would hit in
that search, including the name of the Package that contains it.

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

    a   n   0   ,   up           keypad0         f1    f11
    b   o   1   .   down         keypad1         f2    f12
    c   p   2   \   left         keypad2         f3    f13
    d   q   3   /   right        keypad3         f4    f14
    e   r   4   ;   insert       keypad4         f5    f15
    f   s   5   '   delete       keypad5         f6    f16
    g   t   6   `   home         keypad6         f7    f17
    h   u   7   +   end          keypad7         f8    f18
    i   v   8   -   pageup       keypad8         f9    f19
    j   w   9   =   pagedown     keypad9         f10   f20
    k   x       [   backspace    keypad_period
    l   y       ]   tab          keypad_divide
    m   z           enter        keypad_multiply
                    pause        keypad_minus
                    escape       keypad_plus
                    space        keypad_enter
                    break        clear
                    context_menu
    \___/   ^   ^     ^            ^             \_______/
      |     |   |     |            |                 |
      |     |   |     |            |                 +-- F_KEYS
      |     |   |     |            +-- KEYPAD_KEYS
      |     |   |     +-- NAMED_KEYS
      |     |   +-- SYMBOL_KEYS
      |     +-- NUMBER_KEYS
      +-- LETTER_KEYS

    The above enumerator names are from the ``KeyGroup`` class.

in that order.  Indexing into the list will be done using ``class
ModifierKeyBit`` bits.  Thus somewhere in the decoding will be
something like this:

Note:  this modifier-key order is for the report.  This differs from the
modifier-key order of strings necessary in the "keys" entries, where
the order must be "ctrl", "alt", "shift" to form consistent dictionary
entries.  In fact, because Sublime Text allows users to combine these
modifier key name strings in different orders, it is necessary to parse
those strings and re-code them to ensure they are in a consistent order
to be able to serve as a dictionary key.  The `ModifierKeyBit` class
will serve to help index into the list above.


Ways to Limit Output
====================

Key:
    Cmd:
        KBR = KeyBindingReportCommand
        WBR = WhichBindingReportCommand
    key
        I   = ignored

class KeyGroup(IntEnum):
    ALL           = -3
    KEY           = -2

    KEY_SEQUENCES = -1  # Multiple-key-press sequences, e.g. ["ctrl+k", "ctrl+u"]
    LETTER_KEYS   = 0
    NUMBER_KEYS   = 1
    SYMBOL_KEYS   = 2
    NAMED_KEYS    = 3
    KEYPAD_KEYS   = 4
    F_KEYS        = 5

+-----------------------------------------+-----+--------------------------------------+
| Description                             | Cmd |             Arguments                |
|                                         |     +-----------+---------------+----------+
|                                         |     | package   | key_group     | key_name |
+=========================================+=====+===========+===============+==========+
| By Package.  Output all key bindings    | KBR | 'pkgname' | ALL           | I        |
| contained in Package (e.g. Default or   |     |           |               |          |
| a 3rd-party Package). This also implies |     |           |               |          |
| that the look-up data structures can    |     |           |               |          |
| also be limited to that Package.        |     |           |               |          |
+-----------------------------------------+-----+-----------+---------------+----------+
| By specified key.  Output that key's    | KBR | None      | KEY           | 'a'      |
| bindings in all Packages that contain   |     |           |               |          |
| binding(s) for that key.                |     |           |               |          |
+-----------------------------------------+-----+-----------+---------------+----------+
| By specified key limited to a Package.  | KBR | 'pkgname' | KEY           | 'a'      |
| Output all of key's binding(s).         |     |           |               |          |
+-----------------------------------------+-----+-----------+---------------+----------+
| By specified ``KeyGroup``, using        | KBR | None      | KEY_SEQUENCES | I        |
| bindings from all Packages.             |     |           | - F_KEYS      |          |
+-----------------------------------------+-----+-----------+---------------+----------+
| By specified ``KeyGroup``, limited      | KBR | 'pkgname' | KEY_SEQUENCES | I        |
| to a Package.                           |     |           | - F_KEYS      |          |
+-----------------------------------------+-----+-----------+---------------+----------+
| By specified key based on current scope.| WBR |        ["ctrl+k", "ctrl+b"]          |
| Report binding selected the same way    |     |           ["ctrl+shift+p"]           |
| Sublime Text selects it:  reverse search|     |                 etc.                 |
| selecting first binding where           |     |                                      |
| current scope matches key context.      |     |                                      |
+-----------------------------------------+-----+--------------------------------------+

"""

from datetime import datetime
from typing import List, Tuple, Dict, Optional
import pprint  # For human-readable data dumps when debugging.
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
    assert kbr_setting.default is not None, '`kbr_setting.default` must exist before calling `kbr_setting()`.'
    assert kbr_setting.obj is not None, '`kbr_setting.obj` must exist before calling `kbr_setting()`.'
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
    ALL_KEYS      = -3
    SPECIFIED_KEY = -2
    KEY_SEQUENCES = -1  # Multiple-key-press sequences, e.g. ["ctrl+k", "ctrl+u"]

    LETTER_KEYS   = 0
    NUMBER_KEYS   = 1
    SYMBOL_KEYS   = 2
    NAMED_KEYS    = 3
    F_KEYS        = 4
    KEYPAD_KEYS   = 5

    LAST          = 5
    COUNT         = 6


class ModifierKeyBit(IntFlag):
    SHIFT         = 0b001
    CTRL          = 0b010
    ALT           = 0b100

    NONE          = 0b000
    ALL           = 0b111
    ANY           = 0b111


class FlagBit(IntFlag):
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
        Number of key-presses in binding.
        """
        return len(self.json_binding['keys'])

    def keys(self) -> list:
        return self.json_binding['keys']

    def keys_as_tuple(self) -> tuple:
        return tuple(self.json_binding['keys'])

    def command(self) -> str:
        return self.json_binding['keys']

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

# Key Name Groups, indexed by class ``KeyGroup``.
key_name_groups = [
    # LETTER_KEYS   = 0
    ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'],
    # NUMBER_KEYS   = 1
    ['0','1','2','3','4','5','6','7','8','9'],
    # SYMBOL_KEYS   = 2
    [',','.','\\','/',';',"'",'`','+','-','=','[',']'],
    # NAMED_KEYS    = 3
    ['up','down','left','right','insert','delete','home','end','pageup','pagedown','backspace','tab','enter','pause','escape','space','break','context_menu'],
    # KEYPAD_KEYS   = 4
    ['keypad0','keypad1','keypad2','keypad3','keypad4','keypad5','keypad6','keypad7','keypad8','keypad9','keypad_period','keypad_divide','keypad_multiply','keypad_minus','keypad_plus','keypad_enter','clear'],
    # F_KEYS = 5
    ['f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12','f13','f14','f15','f16','f17','f18','f19','f20'],
    # KEY_SEQUENCES = 6  # Key combos with more than one key-press
]

# Generate ``key_names`` from ``key_name_groups``.
count = 0

for grp in key_name_groups:
    count += len(grp)

# Pre-allocate array instead of 103 ``append()`` calls (inefficient).
key_names = [None] * count
i = 0

for grp in key_name_groups:
    for key_name in grp:
        key_names[i] = key_name
        i += 1

# Generate ``key_index_by_key_name_dict`` from ``key_names``.
# This dictionary's values index into ``key_names``, while also giving
# each key name an integer value.  This enables us to produce a unique
# integer value for each possible key with all 8 modifier possibilities
# with something like this:
#
#     keypress_id = (i << 3) | modifier_value
#
# where ``modifier_value`` is comprised of OR-ed bits from ModifierKeyBit.
key_index_by_key_name_dict = {}

for i, key_name in enumerate(key_names):
    key_index_by_key_name_dict[key_name] = i

# Create 2 lookup data structures.
gdictByMainKey = {}
gdictByKeySquence = {}

# Clean up.
del i, count, grp, key_name


# =========================================================================
# Function Definitions
# =========================================================================

def _add_binding_to_main_key_dict(binding: KeyBinding):
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
    assert binding.keypress_count() == 1, f'Number of elements in `keys` expected 1, got {binding.keypress_count()}!'
    debugging = is_debugging(DebugBits.BUILDING_MAIN_KEY_DICT)
    if debugging:
        print('In _add_binding_to_main_key_dict()...')

    global gdictByMainKey
    lsWorkingKeypress = keypress_str = binding.keys()[0]

    if debugging:
        print(f'  {keypress_str=}')

    # Here we know gdictByMainKey[main_key_name] exists.
    key_modifier_index = 0

    modifier_str = 'shift+'
    if modifier_str in lsWorkingKeypress:
        key_modifier_index |= ModifierKeyBit.SHIFT
        lsWorkingKeypress = lsWorkingKeypress.replace(modifier_str, '')

    modifier_str = 'ctrl+'
    if modifier_str in lsWorkingKeypress:
        key_modifier_index |= ModifierKeyBit.CTRL
        lsWorkingKeypress = lsWorkingKeypress.replace(modifier_str, '')

    modifier_str = 'alt+'
    if modifier_str in lsWorkingKeypress:
        key_modifier_index |= ModifierKeyBit.ALT
        lsWorkingKeypress = lsWorkingKeypress.replace(modifier_str, '')

    # Now ``keypress_str`` contains just the name of the main key.
    main_key_name = lsWorkingKeypress
    assert main_key_name in keypress_str, f'  ERROR!  Somehow [{main_key_name}] is not in [{keypress_str}].'
    # if debugging:
    #     print(f'  Computed modifier: [0b{key_modifier_index:03b}]')

    if main_key_name not in gdictByMainKey:
        if debugging:
            print(f'  ERROR!  Found key name [{main_key_name}] not in gdictByMainKey.')
        empty_list = [None] * 8
        gdictByMainKey[main_key_name] = empty_list

    by_main_key_item = gdictByMainKey[main_key_name]
    key_binding_list = by_main_key_item[key_modifier_index]

    if key_binding_list is None:
        # Lazy list creation
        by_main_key_item[key_modifier_index] = []
        key_binding_list = by_main_key_item[key_modifier_index]

    key_binding_list.append(binding)
    # if debugging:
    #     print(f'  Added [{keypress_str}] binding to item [{key_modifier_index}].')

    #keys, cmd, args, ctxt = binding.extracted_json_parts()
    #print(f'{keys=}, {cmd=}, {args=}, {ctxt=}')


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
    debugging = is_debugging(DebugBits.BUILDING_KEY_SEQ_DICT)
    if debugging:
        print('In _add_binding_to_key_seq_dict()...')

    global gdictByKeySquence
    keys_tpl = binding.keys_as_tuple()

    if keys_tpl not in gdictByKeySquence:
        # Lazy creation.
        gdictByKeySquence[keys_tpl] = []

    binding_list = gdictByKeySquence[keys_tpl]
    binding_list.append(binding)
    if debugging:
        print(f'  Added binding for {keys_tpl}.')
    # keys, cmd, args, ctxt = binding.extracted_json_parts()
    # print(f'{keys=}, {cmd=}, {args=}, {ctxt=}')


def _include_in_lookup_data(path: str, pkg_name: str, file_name: str):
    lsRsrc = sublime.load_resource(path)
    llstJsonKmaps = sublime.decode_value(lsRsrc)

    for json_kmap in llstJsonKmaps:
        binding = KeyBinding(json_kmap, pkg_name, file_name)
        if binding.keypress_count() > 1:
            _add_binding_to_key_seq_dict(binding)
        else:
            _add_binding_to_main_key_dict(binding)


def _build_empty_main_key_dict():
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
    debugging = is_debugging(DebugBits.BUILDING_MAIN_KEY_DICT)
    if debugging:
        print('In _build_empty_main_key_dict()')
    global gdictByMainKey
    for key_name in key_names:
        empty_list = [None] * 8
        gdictByMainKey[key_name] = empty_list

    # if debugging:
    #     print('  Empty by-main-key dict:')
    #     print(repr(gdictByMainKey))


def build_lookup_data(
        package  : str      = 'Default',
        key_group: KeyGroup = KeyGroup.F_KEYS,
        key_name : str      = ''
        ):
    """
    Build lookup data required by the report dictated by the 3 arguments.
    The descriptions in the table below are for the output, but they also have
    implications about the data required to support them.  And we don't gather
    information that won't be needed.  For example, if the Package is limited
    to the ``Default`` Package, then there is no need to process any other
    ``.sublime-keymap`` files.

    Key:
        I = ignored

    +-----------------------------------------+----------------------------------+
    | Description                             |          Arguments               |
    |                                         +---------+-------------+----------+
    |                                         | package | key_group   | key_name |
    +=========================================+=========+=============+==========+
    | By Package.  Output all key bindings    |'pkgname'| ALL         | I        |
    | contained in Package (e.g. Default or   |         |             |          |
    | a 3rd-party Package). This also implies |         |             |          |
    | that the look-up data structures can    |         |             |          |
    | also be limited to that Package.        |         |             |          |
    +-----------------------------------------+---------+-------------+----------+
    | By specified key limited to a Package.  |'pkgname'| KEY         | 'a'      |
    | Output all of key's binding(s).         |         |             |          |
    +-----------------------------------------+---------+-------------+----------+
    | By specified key.  Output that key's    | None    | KEY         | 'a'      |
    | bindings in all Packages that contain   |         |             |          |
    | binding(s) for that key.                |         |             |          |
    +-----------------------------------------+---------+-------------+----------+
    | By specified ``KeyGroup``, using        | None    |KEY_SEQUENCES| I        |
    | bindings from all Packages.             |         |- F_KEYS     |          |
    +-----------------------------------------+---------+-------------+----------+
    | By specified ``KeyGroup``, limited      |'pkgname'|KEY_SEQUENCES| I        |
    | to a Package.                           |         |- F_KEYS     |          |
    +-----------------------------------------+---------+-------------+----------+

    :param package:    Name of package; None or '' when not applicable
    :param key_group:  Which key group to report on
    :param key_name:   Key name; ignored when not applicable
    :return:  None
    """
    debugging = is_debugging(DebugBits.FILTERING)
    if debugging:
        print(f'In build_lookup_data({package=})')

    global gdictByMainKey
    global gdictByKeySquence
    # Start fresh.
    gdictByMainKey = {}
    gdictByKeySquence = {}

    keymap_paths = sublime.find_resources('*.sublime-keymap')
    _build_empty_main_key_dict()

    for path in keymap_paths:
        print(f'{path=}')
        match = pkg_name_from_resource_path_re.search(path)

        # Pattern recognized?
        if not match:
            if debugging:
                print(f'  >>> ERROR >>> Pattern not recognized!  [{path}]')
            continue

        pkg_name = match[1]

        # Filter out Packages other than ``package``.
        if pkg_name != package:
            if debugging:
                print(f'  Package mismatch:  [{package}] != [{pkg_name}]')
            continue

        if debugging:
            print(f'  Matches pkg[{package}]:  {path}')
        file_name = match[2]

        if 'Default (' in file_name:
            # Platform specific key binding---only use if platform matches.
            use_it = ((platform_name_w_parens in file_name))

            if not use_it:
                if debugging:
                    print(f'  Not a platform match:  {file_name}.')
                continue
            else:
                if debugging:
                    print(f'  Platform match:  {file_name}.')
        else:
            use_it = True

        if use_it:
            if debugging:
                print(f'  Using {file_name}.')
            _include_in_lookup_data(path, pkg_name, file_name)
        else:
            if debugging:
                print(f'  Not using {file_name}.')


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
