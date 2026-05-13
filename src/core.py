r"""
KeyBindingReport
****************

Definitions
===========

key-modifier code
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

keypress_list
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
    and the key-modifier value:

        encoded_keypress = (i << 4) | modifier_value

    where:

    - ``i`` is the key ID (index into the ``core.all_key_names`` list), and
    - ``modifier_value`` is comprised of OR-ed bits from ``ModifierKeyBits``.

    While the key-modifier code only needs 3 bits, 4 bits is used so its parts can
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

ReportKeyBinding object
    an instance of the ``ReportKeyBinding`` class, containing the JSON key-binding
    object from a ``.sublime-keymap`` file (defining the binding of an individual
    keypress/keypress sequence), plus some additional data:  the name of the
    Package and ``.sublime-keymap`` file it came from.

    Note that during instantiation of a new ``ReportKeyBinding`` object, the
    JSON key-binding object's "keys" value is converted from a list to
    a tuple for ease of use as dictionary keys and in sets.

-----


Design Factor
=============

In the ``Default`` Package and in most other places where official ``.sublime-keymap``
files can be found, the "keys" entry (e.g. ``"keys": ["alt+shift+up"]``) in each
JSON key-binding object has a specific order of modifier-key strings among the '+'
characters, and it is always in this sequence:

- command
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

Each such list item then contains ``None`` or a list of ``ReportKeyBinding``
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
        "a": [  <-- binding_lists_by_mod_code
                None,   # binding list for unmodified 'a' key
                None,   # binding list for [Shift-a]
                [...],  # binding list for [Ctrl-a]       <-- binding_list
                [...],  # binding list for [Ctrl-Shift-a] <-- binding_list
                None,   # binding list for [Alt-a]
                None,   # binding list for [Alt-Shift-a]
                None,   # binding list for [Alt-Ctrl-a]
                None,   # binding list for [Alt-Ctrl-Shift-a]
                None,   # binding list for [Command-a]
                None,   # binding list for [Command-Shift-a]
                [...],  # binding list for [Command-Ctrl-a]       <-- binding_list
                [...],  # binding list for [Command-Ctrl-Shift-a] <-- binding_list
                None,   # binding list for [Command-Alt-a]
                None,   # binding list for [Command-Alt-Shift-a]
                None,   # binding list for [Command-Alt-Ctrl-a]
                None,   # binding list for [Command-Alt-Ctrl-Shift-a]
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
                ReportKeyBinding object,
                ReportKeyBinding object,
                ReportKeyBinding object,
                ...
            ]


Main Key Names
==============

When modifier keys are used in :term:`keypresses <keypress>`, these unshifted key
names must be used with them:

.. code-block:: text

                                                        Alternate      Specialty
                    Regular Key Names                   Symbol Names   Keyboards
    --------------------------------------------------  -------------  -----------------
    0   a   n   f1   ,   keypad0          up            backquote      close
    1   b   o   f2   .   keypad1          down          equals         copy
    2   c   p   f3   \   keypad2          left          forward_slash  cut
    3   d   q   f4   /   keypad3          right         minus          find
    4   e   r   f5   ;   keypad4          insert        plus           open
    5   f   s   f6   '   keypad5          delete                       paste
    6   g   t   f7   `   keypad6          home                         redo
    7   h   u   f8   -   keypad7          end                          save
    8   i   v   f9   =   keypad8          pageup                       sysreq
    9   j   w   f10  [   keypad9          pagedown                     undo
        k   x   f11  ]   keypad_period    backspace
        l   y   f12      keypad_divide    tab                          browser_back
        m   z   f13      keypad_multiply  enter                        browser_favorites
                f14      keypad_minus     pause                        browser_forward
                f15      keypad_plus      break                        browser_home
                f16      keypad_enter     space                        browser_refresh
                f17      clear            escape                       browser_search
                f18                       context_menu                 browser_stop
                f19
                f20
    ^   \___/    ^   ^     ^              \______________________________________________/
    |     |      |   |     |                                |
    |     |      |   |     |                                +-- NAMED_KEYS
    |     |      |   |     +-- KEYPAD_KEYS
    |     |      |   +-- SYMBOL_KEYS
    |     |      +-- F_KEYS
    |     +-- LETTER_KEYS
    +-- NUMBER_KEYS

The above names in ALL CAPS are from the ``KeyGroup`` class.
Note that they identify lists of key names that are mutually exclusive,
as well as provide indexes into ``key_name_groups`` list for values >= 0.

Shifted key names can also be used, but *may not be used with modifier keys*.
Attempting to do so generates no errors, but does not work.

.. code-block:: text

    "  (  )  {  }                  # <-- These can be found in Default keymap
                                   #     with contexts.

    `  ~  !  @  #  $  %  ^  &      # <-- These are also bind-able (and should
    *  _  +  |  :  "  <  >  ?      #     have contexts if used).

    " "                            # <-- Works as an unmodified key,
                                   #     but is redundant with `space`.

The following is a specialty application, such as if your Plugin temporarily
either suppresses or captures all keystrokes with a custom key context.
This key name (with angle brackets) captures all printable keypresses:

.. code-block:: text

    <character>


Ways to Limit Output
====================

See ``KeyBindingReportCommand`` docstring for details.

"""

from datetime import datetime
import sublime
# Importing ``IntFlag`` in the below is to remain compatible with Python 3.8,
# which requires it.  Python 3.14 does not.
from ..lib.debug import IntFlag, DebugBits, is_debugging, set_debugging_bits  # noqa: F401
from ..keybindingreport import package_name



# *************************************************************************
# Configuration
# *************************************************************************

# Use name of parent directory as `package_name`.
_cfg_pkg_settings_file                   = package_name + '.sublime-settings'

# Track on-settings-changed listener.
_cfg_on_settings_chgd_listener_id        = '_kbr_settings_changed_tag'

# Package Settings Names (most are used multiple times throughout this Plugin)
_cfg_stg_name__debugging                 = 'debugging'
_cfg_stg_name__rst_container_class       = 'rst_container_class'
_cfg_stg_name__output_directory_windows  = 'output_directory_windows'
_cfg_stg_name__output_directory_linux    = 'output_directory_linux'
_cfg_stg_name__output_directory_osx      = 'output_directory_osx'
_cfg_stg_name__timestamp_strftime_format = 'timestamp_strftime_format'



# *************************************************************************
# Package Settings
# *************************************************************************

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



# *************************************************************************
# Load default settings once.
# *************************************************************************

kbr_setting.default = {
    _cfg_stg_name__output_directory_windows : "",
    _cfg_stg_name__output_directory_linux   : "",
    _cfg_stg_name__output_directory_osx     : "",
    _cfg_stg_name__rst_container_class      : "",
    _cfg_stg_name__timestamp_strftime_format: "%Y-%m-%d %H:%M",
    _cfg_stg_name__debugging                : False,
}

setting__output_directory_windows  = kbr_setting.default[_cfg_stg_name__output_directory_windows]
setting__output_directory_linux    = kbr_setting.default[_cfg_stg_name__output_directory_linux]
setting__output_directory_osx      = kbr_setting.default[_cfg_stg_name__output_directory_osx]
setting__rst_container_class       = kbr_setting.default[_cfg_stg_name__rst_container_class]
setting__timestamp_strftime_format = kbr_setting.default[_cfg_stg_name__timestamp_strftime_format]
setting__debugging                 = kbr_setting.default[_cfg_stg_name__debugging]


def show_settings():
    print(f'{setting__output_directory_windows  = }')
    print(f'{setting__output_directory_linux    = }')
    print(f'{setting__output_directory_osx      = }')
    print(f'{setting__rst_container_class       = }')
    print(f'{setting__timestamp_strftime_format = }')
    print(f'{setting__debugging                 = }')



# *************************************************************************
# Utilities
# *************************************************************************

def timestamp() -> str:
    """ Universal timestamp; used in some Package debug output. """
    now = datetime.now()
    fmt = kbr_setting(_cfg_stg_name__timestamp_strftime_format)
    return now.strftime(fmt)


def arg_type_error_message(arg, arg_name: str, required_type: str, after_matter: str = ''):
    c = required_type[0]
    article = 'a'
    if c in 'aeiou':
        article = 'an'

    return f'`{arg_name}` arg must be {article} {required_type}. Got {type(arg)} instead.{after_matter}'



# *************************************************************************
# Events
# *************************************************************************

def _on_pkg_settings_chgd():
    """
    Take action after Package settings have changed.
    """
    # Load overridable Package settings.
    # `kbr_setting()` cannot be called until this is done, and
    # `is_debugging()` will return an incorrect value until this is done.
    kbr_setting.obj = sublime.load_settings(_cfg_pkg_settings_file)

    # Initialize debugging subsystem.
    bit_val = kbr_setting(_cfg_stg_name__debugging)
    set_debugging_bits(bit_val)
    debugging = is_debugging(DebugBits.SETTINGS_CHANGED_EVENT)
    if debugging:
        print('In _on_pkg_settings_chgd()')

    global setting__output_directory_windows
    global setting__output_directory_linux
    global setting__output_directory_osx
    global setting__rst_container_class
    global setting__timestamp_strftime_format
    global setting__debugging
    setting__output_directory_windows  = kbr_setting(_cfg_stg_name__output_directory_windows)
    setting__output_directory_linux    = kbr_setting(_cfg_stg_name__output_directory_linux)
    setting__output_directory_osx      = kbr_setting(_cfg_stg_name__output_directory_osx)
    setting__rst_container_class       = kbr_setting(_cfg_stg_name__rst_container_class)
    setting__timestamp_strftime_format = kbr_setting(_cfg_stg_name__timestamp_strftime_format)
    setting__debugging                 = kbr_setting(_cfg_stg_name__debugging)

    if debugging:
        show_settings()


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
