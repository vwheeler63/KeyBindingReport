"""
This module does all the data fetching of selected key bindings.

Usage:

    key_groups       = [KeyGroup.NUMBERS]
    key_names        = ["q", "w", "a", "s"]
    keys_list        = [["ctrl+p"], ["ctrl+shift+p"], ["ctrl+k", "ctrl+u"]]
    packages         = ["Default"]
    limit_to_context = False

    key_data = KeyBindingData()
    key_data.generate(key_groups, key_names, keys_list, packages, limit_to_context)

Each time ``key_data.generate()`` is called produces a new data set.
No memory of the previous call remains.
"""
import re
from typing import List, Tuple, Set, Optional, Iterable
from enum import IntEnum, IntFlag
import sublime
from . import core
from ..lib.debug import DebugBits, is_debugging
from ..lib import context
from ..lib import key_binding


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
    [',','.','\\','/',';',"'",'`','-','=','[',']',       # OK with or w/o key modifiers. (Unshifted)
            '"', '(', ')', '[', ']', '{', '}', '`',      # Only w/o key modifiers.       (Shifted)
            '~', '!', '@', '#', '$', '%', '^', '&',      # Only w/o key modifiers.       (Shifted)
            '*', '_', '+', '|', ':', '"', '<', '>', '?'  # Only w/o key modifiers.       (Shifted)
            ],
            # The last 3 rows are added because these "bare" keypresses (i.e. having
            # no ctrl/alt/shift key modifiers) are 100% bind-able in Sublime Text
            # build 4200, and the first 7 of them can be found in the Default keymap.
            # These need to be here for KeyBindingReport to find and report on them
            # in the various keymaps where they occur.
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

# Clean up.
del i, count, grp, key_name


# =========================================================================
# Utilities
# =========================================================================

def main_key_and_modifier_code(keypress_str: str) -> Tuple[str, int]:
    """
    Key-modifier code from `keypress_str` (e.g. "ctrl+alt+shift+p").

    :param keypress_str:  Keypress definition string compatible with
                            Sublime Text `.sublime-keymap` "keys" entries

    See "key-modifier code" and "encoded keypress" in definitions in
    module docstring for details.
    """
    lsWorkingKeypress = keypress_str
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


def encoded_keypress_from_components(main_key_name: str, key_modifier_code: int) -> int:
    """
    Encoded keypress from `main_key_name` and `key_modifier_code`.

    :param main_key_name:       Official name of key, found in `all_key_names`.
                                  (See Key Names in module docstring for the list.)
    :param key_modifier_code:   Integer representation of Ctrl+Alt+Shift key
                                  modifiers accommodating keypress.
                                  (See "key-modifier code" and "encoded keypress"
                                  in definitions in module docstring for details.)
    """
    result = -1

    if main_key_name in key_index_by_key_name_dict:
        i = key_index_by_key_name_dict[main_key_name]
        result = (i << 4) | key_modifier_code

    return result


def encoded_keypress(keypress_str: str) -> int:
    """
    Encoded keypress from `keypress_str` (e.g. "ctrl+alt+shift+p").

    :param keypress_str:  Keypress definition string compatible with
                            Sublime Text `.sublime-keymap` "keys" entries

    See "key-modifier code" and "encoded keypress" in definitions in
    module docstring for details.
    """
    kn, mod_code = main_key_and_modifier_code(keypress_str)
    return encoded_keypress_from_components(kn, mod_code)


# =========================================================================
# Classes
# =========================================================================

class ModifierKeyBits(IntFlag):
    SHIFT         = 0b001
    CTRL          = 0b010
    ALT           = 0b100

    NONE          = 0b000
    ALL           = 0b111
    ANY           = 0b111


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


class ReportKeyBinding(key_binding.KeyBinding):
    """
    Representation of a KeyBinding plus some additional data needed for reporting:

    - package name
    - ``.sublime-keymap`` file name
    """
    __slots__ = ['json_binding', 'pkg_name', 'file_name']

    def __init__(self, decoded_key_binding: dict, pkg_name: str, file_name: str):
        # Incorporate contents of `decoded_key_binding` into `self`.
        super().__init__(decoded_key_binding, pkg_name, file_name)
        # Store extra data for report.
        self.pkg_name     = pkg_name
        self.file_name    = file_name

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
        <ReportKeyBinding pkg=Default { ['"'], move(({'by': 'characters', 'forward': True}))
          "context": [
            { "key": "setting.auto_match_enabled", "operator": "equal"         , "operand": True }
            { "key": "selection_empty"           , "operator": "equal"         , "operand": True, "match_all": True }
            { "key": "following_text"            , "operator": "regex_contains", "operand": '^"', "match_all": True }
            { "key": "selector"                  , "operator": "not_equal"     , "operand": 'punctuation.definition.string.begin', "match_all": True }
            { "key": "eol_selector"              , "operator": "not_equal"     , "operand": 'string.quoted.double - punctuation.definition.string.end', "match_all": True }
          ]
        }>

        or if there is no "context" entry:

        <ReportKeyBinding pkg=Default { ['right'], move({'by': 'characters', 'forward': True}) }>

        """
        binding_str = self.format_binding()
        return f'<{self.__class__.__name__} pkg={self.pkg_name} {binding_str}>'

    def package_name(self) -> str:
        return self.pkg_name

    def keymap_file_name(self) -> str:
        return self.file_name


class KeyBindingData:

    __slots__ = [
        'mdictByMainKey',
        'mdictByKeySquence',
        'view',
        '_debugging_removing_arg_overlap',
        '_debugging_filtering_stage_i',
        '_debugging_filtering_stage_ii',
        '_debugging_building_main_key_dict',
        '_debugging_building_key_seq_dict'
    ]

    def __init__(self):
        self.mdictByMainKey = {}
        self.mdictByKeySquence = {}

        self.view = None

        self._debugging_removing_arg_overlap   = is_debugging(DebugBits.REMOVING_ARG_OVERLAP)
        self._debugging_filtering_stage_i      = is_debugging(DebugBits.FILTERING_STAGE_I)
        self._debugging_filtering_stage_ii     = is_debugging(DebugBits.FILTERING_STAGE_II)
        self._debugging_building_main_key_dict = is_debugging(DebugBits.BUILDING_MAIN_KEY_DICT)
        self._debugging_building_key_seq_dict  = is_debugging(DebugBits.BUILDING_KEY_SEQ_DICT)

    def generate(self,
            key_groups      : Optional[Iterable[KeyGroup]] = None,
            key_names       : Optional[Iterable[str]] = None,
            keys_list       : Optional[Iterable[Iterable[str]]] = None,
            packages        : Optional[Iterable[str]] = None,
            limit_to_context: bool = False,
            ):
        r"""
        Generate Key-Binding data, based on argument values provided, if any.
        ``key_groups``, ``key_names``, ``keys_list`` are added together, any
        overlap removed, and then limited by ``packages``.

        Precondition:   ``key_groups``, ``key_names``, ``keys_list`` and ``packages``
                        must each be a list, set, tuple or ``None``.

        Parameters:
        -----------
        :param self:        Instance of ``KeyBindingData``; all data is
                            connected to this instance.

        :param key_groups:  List of ``KeyGroup`` integers, adding keys from these
                            groups to the data gathered.  ``KeyGroup.ALL`` is
                            equivalent to specifying all the other key groups.
                            ``None`` or ``[]`` when the only keys that should
                            be included are in ``key_names`` and ``keys_list``.

        :param key_names:   List of individual key names.  Each key in this list
                            specifies including all possible key-modifier
                            combinations with this key.  Each key only has
                            an impact on data gathered if it is found in
                            ``all_key_names``.
                            ``None`` or ``[]`` when not applicable.

        :param keys_list:   List of "keys" (same format as "keys" elements
                            from JSON key bindings) e.g.

                                [["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]].

                            Meaning:  include key bindings with these "keys".
                            these specific keypresses/keypress sequences.
                            ``None`` or ``[]`` when not applicable.

        :param packages:    List of package names data should be limited to;
                            ``None`` or ``[]`` when packages are not limited.

        :param limit_to_context:
                            Whether to NOT include key bindings with context
                            entries that do not match current circumstances (i.e.
                            selection locations, surrounding text, scope, etc.).
                            When ``True``, this command excludes key bindings
                            that do not match the context of the active View.
                            (Takes longer.)

        :return:  None


        Usage:
        ------

        key_groups       = [KeyGroup.NUMBERS]
        key_names        = ["q", "w", "a", "s"]
        keys_list        = [["ctrl+p"], ["ctrl+shift+p"], ["ctrl+k", "ctrl+u"]]
        packages         = ["Default"]
        limit_to_context = False

        key_data = KeyBindingData()
        key_data.generate(key_groups, key_names, keys_list, packages, limit_to_context)

        class KeyGroup(IntEnum):
            # Non-negative values index into ``key_name_groups``.
            ALL            = -2  # Equivalent to specifying all groups >= 0.
            KEY_SEQUENCES  = -1  # Multiple-keypress sequences, e.g. ["ctrl+k", "ctrl+u"]

            LETTER_KEYS    =  0  # \
            NUMBER_KEYS    =  1  #  \
            F_KEYS         =  2  #   \__ These index into ``key_name_groups``.
            SYMBOL_KEYS    =  3  #   /
            NAMED_KEYS     =  4  #  /
            KEYPAD_KEYS    =  5  # /

        class FlagBits(IntFlag):
            SHOW_UNBOUND_KEY_COMBINATIONS = 0b00000001
            SHOW_PACKAGE_NAME             = 0b00000010
            ADD_COMMENTS_COLUMN           = 0b00000100
            INCLUDE_UNTRANSLATED_CONTEXTS = 0b00001000
            INCLUDE_ENGLISH_CONTEXTS      = 0b00010000

            NONE                          = 0b00000000
            ALL                           = 0b11111111
            ANY                           = 0b11111111

        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | Description                   |packages   |key_groups   |key_names | keys_list                              |
        +===============================+===========+=============+==========+========================================+
        | By Package:  output all key   |['pkgname']| None or []  |None or []| None or []                             |
        | bindings contained in Package |           |             |          |                                        |
        | (e.g. Default or a 3rd-party  |           |             |          |                                        |
        | Package)                      |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified key limited      |['pkgname']| None or []  |['a', ...]| None or []                             |
        | to a Package:  output all     |           |             |          |                                        |
        | of key's binding(s)           |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified key:  output     |None or [] | None or []  |['a', ...]| None or []                             |
        | that key's bindings in all    |           |             |          |                                        |
        | Packages that contain         |           |             |          |                                        |
        | binding(s) for that key       |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified ``KeyGroup``     |None or [] |[F_KEYS, ...]|None or []| None or []                             |
        | using bindings from all       |           |             |          |                                        |
        | Packages.                     |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified ``KeyGroup``     |['pkgname']|[F_KEYS, ...]|None or []| None or []                             |
        | limited to a Package.         |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified ``keys_list``    |None or [] | None or []  |None or []|[["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]]|
        | for all Packages.             |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+


        How conflicts in input-limiting arguments are resolved:
        -------------------------------------------------------
        1.  Each list provided has duplicates removed.  Part of doing that
            for ``keys_list`` if present is converting its elements to
            tuples so they can more efficiently have duplicates removed
            since tuples can use operators like `==`, `!=`, `in` and be
            keys in dictionaries.  In doing so create:

                ``keys_tuples_set``

        2.  If both ``key_names`` and ``key_groups`` are provided and are
            not empty, the result is additive in a logical way:
            ``key_names`` only has an effect for the keys specified that
            fall *outside* any of the other key groups specified.  This is
            accomplished by removing from ``key_names`` any "keys" items
            whose main key also appears in any of the specified key
            groups.

            From these two, if either of them were specified, a list of
            accepted keys is built, or left as ``None`` if there are no
            restrictions on which keys are reported on.  Namely:
            ``include_key_name_set``.

        3.  If (include_key_name_set is not None and ``keys_tuples_set`` is not None),
            this indicates the user has specified a ``keys_tuples_set`` which *may*
            have overlap with ``include_key_name_set``.  Since the latter
            means "report on all possible key combinations for these keys",
            any keypress/keypress sequence present in ``keys_tuples_set`` which
            has one of those key names as the main key would be redundant and
            is removed from ``keys_tuples_set``.

        4.  Finally, "overlap" may occur if:

            - ``keys_tuples_set`` and ``key_groups`` were both provided and not empty,
            - it contains any multiple keypress sequences, and
            - KEY_SEQUENCES was included in ``key_groups``,

            then all such entries in ``keys_tuples_set`` would be redundant since
            their occurrence would already be covered by the KEY_SEQUENCES
            key group.


        How Resulting Args Are Prepared
        -------------------------------
        include_key_name_set = None

        If ``key_groups`` was provided:
            include_key_name_set = Unique list of accepted key
            names based on ``key_groups``.

        If ``keys_list`` was provided, ``keys_tuples_set`` is created from it.
            The above conflict/overlap resolution removed anything already
            covered by other arguments.  If there is nothing left, then
            ``keys_tuples_set`` is set to ``None``.

        Finally, all 3 of:

        - packages,
        - include_key_name_set, and
        - keys_tuples_set are passed to

        ``self._build_report_data()``.


        How Resulting Args Are Processed
        --------------------------------
        See ``self._build_report_data()`` docstring for details.
        """

        # ---------------------------------------------------------------------
        # Enforce precondition.
        # ---------------------------------------------------------------------
        req_type = 'list, tuple or set'
        after_msg = '  Aborting.'
        if key_groups:
            if not self._is_list_tuple_or_set(key_groups):
                msg = core.arg_type_error_message(key_groups, 'key_groups', req_type, after_msg)
                raise TypeError(msg)
        if keys_list:
            if not self._is_list_tuple_or_set(keys_list):
                msg = core.arg_type_error_message(keys_list, 'keys_list', req_type, after_msg)
                raise TypeError(msg)
            # If execution arrives here, then we need to also test its members.
            for keypresses in keys_list:
                if not self._is_list_tuple_or_set(keypresses):
                    msg = f'  Each of the keypresses in `keys_list` arg must be a {req_type}.' \
                          f'  At least 1 was type {type(keypresses)}.{after_msg}'
                    raise TypeError(msg)
        if packages:
            if not self._is_list_tuple_or_set(packages):
                msg = core.arg_type_error_message(packages, 'packages', req_type, after_msg)
                raise TypeError(msg)

        # ---------------------------------------------------------------------
        # Remove duplicates from limiting args, pursuant to:
        #
        # 1.  Each list provided has duplicates removed.  Part of doing that
        #     for ``keys_list`` if present is converting its elements to
        #     tuples so they can more efficiently have duplicates removed
        #     since tuples can use operators like `==`, `!=`, `in` and be
        #     keys in dictionaries.
        # ---------------------------------------------------------------------
        debugging = self._debugging_removing_arg_overlap

        if key_groups and type(key_groups) != set:
            key_groups = set(key_groups)
        if key_names and type(key_names) != set:
            key_names = set(key_names)

        keys_tuples_set = None
        if keys_list:
            # Remember:  this is a Iterable of Iterables, e.g.
            # [["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]].
            # Lists cannot be used in sets or as dictionary keys.  So we need
            # to convert its items to tuples regardless of how many there are.
            # And we need to later assume ``keys_list`` is a set.
            # VITAL:  it's vital that `keys_tuples_set` contains TUPLES since
            # tuples can use operators like `==`, `!=`, `in` and be keys
            # in dictionaries!
            keys_tuples_set = set()
            for keypresses in keys_list:
                keys_tuples_set.add(tuple(keypresses))

        if packages and type(packages) != set:
            packages = set(packages)

        # All of packages, key_groups, key_names, keys_tuples_set are now set objects.

        if debugging:
            print('After removing duplicates:')
            print(f'  {key_groups=}')
            print(f'  {key_names=}')
            print(f'  {keys_tuples_set=}')
            print(f'  {packages=}')

        # ---------------------------------------------------------------------
        # Prepare ``include_key_name_set`` while removing overlap from
        # ``key_groups`` and ``keys_tuples_set` if both are present, pursuant to:
        #
        # 2.  If both ``key_names`` and ``key_groups`` are provided and are
        #     not empty, the result is additive in a logical way:
        #     ``key_names`` only has an effect for the keys specified that
        #     fall *outside* any of the other key groups specified.  This is
        #     accomplished by removing from ``key_names`` any "keys" items
        #     whose main key also appears in any of the specified key
        #     groups.
        #
        #     From these two, if either of them were specified, a list of
        #     accepted keys is built, or left as ``None`` if there are no
        #     restrictions on which keys are reported on.  Namely:
        #     ``include_key_name_set``.
        # ---------------------------------------------------------------------
        include_key_name_set = None   # None == no limits on key-names.

        if key_groups or key_names:
            include_key_name_set = set()
            if key_groups:
                # Load it with key names from the specified groups.
                if KeyGroup.ALL in key_groups:
                    include_key_name_set.update(all_key_names)
                else:
                    for key_grp_idx in key_groups:
                        if key_grp_idx >= 0:
                            key_grp_list = key_name_groups[key_grp_idx]
                            include_key_name_set.update(key_grp_list)

            # Now ``include_key_name_set`` contains keys in ``key_groups``
            # if ``key_groups`` was specified, or is empty if not.  If not empty,
            # it gives us an intermediate list against which to check whether
            # there is any overlap in ``key_names``, in case both were specified.
            # Example ``key_names``:  ["k", "u", "f6", "enter"].
            if key_names and include_key_name_set:
                # Remove any overlap in ``key_names`` resulting from any items in
                # ``key_names`` that also appear in ``include_key_name_set``.
                key_names_copy = key_names.copy()

                for key_name in key_names_copy:
                    if key_name in include_key_name_set:
                        key_names.remove(key_name)

            # Finally, add any names remaining in ``key_names`` into list.
            if key_names:
                include_key_name_set.update(key_names)

        if debugging:
            print('After removing overlap phase I:')
            print(f'  {key_names=}')
            print(f'  {include_key_name_set=}')

        # -----------------------------------------------------------------
        # Remove possible overlap between ``include_key_name_set``
        # and ``keys_tuples_set`` if both are present, pursuant to:
        #
        # 3.  If (include_key_name_set is not None and keys_tuples_set is not None),
        #     this indicates the user has specified a ``keys_tuples_set`` which *may*
        #     have overlap with ``include_key_name_set``.  Since the latter
        #     means "report on all possible key combinations for these keys",
        #     any keypress/keypress sequence present in ``keys_tuples_set`` which
        #     has one of those key names as the main key would be redundant and
        #     is removed from ``keys_tuples_set``.
        #
        # Example:
        # [("ctrl+k", "ctrl+u"), ("ctrl+p"), ("ctrl+shift+p")]
        # -----------------------------------------------------------------
        if include_key_name_set and keys_tuples_set:
            keys_tuples_set_copy = keys_tuples_set.copy()

            print(f'{keys_tuples_set_copy=}')

            for keypress_tuple in keys_tuples_set_copy:
                if len(keypress_tuple) == 1:
                    keypress = keypress_tuple[0]
                    key_name, _ = main_key_and_modifier_code(keypress)
                    if key_name in include_key_name_set:
                        # Overlap
                        if debugging:
                            print(f'Removing overlap with key {key_name} in {keypress_tuple}.')
                        keys_tuples_set.remove(keypress_tuple)

        if debugging:
            print('After removing overlap phase II:')
            print(f'  {keys_tuples_set=}')
            print(f'  {include_key_name_set=}')

        # -----------------------------------------------------------------
        # Remove possible overlap between ``key_groups`` and ``keys_tuples_set``
        # if both are present, pursuant to:
        #
        # 4.  Finally, "overlap" may occur if:
        #
        #     - ``keys_tuples_set`` and ``key_groups`` were both provided and not empty,
        #     - it contains any multiple keypress sequences, and
        #     - KEY_SEQUENCES or ALL was included in ``key_groups``,
        #
        #     then all such entries in ``keys_tuples_set`` would be redundant since
        #     their occurrence would already be covered by the KEY_SEQUENCES
        #     or ALL key group.
        # -----------------------------------------------------------------
        if key_groups:
            sequences_in_key_groups = (( KeyGroup.KEY_SEQUENCES in key_groups ))
            all_in_key_groups = (( KeyGroup.ALL in key_groups ))
        else:
            sequences_in_key_groups = False
            all_in_key_groups = False

        incl_all_multi_key_seqs = ((
                key_groups is not None
                and len(key_groups) > 0
                and (sequences_in_key_groups or all_in_key_groups)
                ))

        if keys_tuples_set and incl_all_multi_key_seqs:
            keys_tuples_set_copy = keys_tuples_set.copy()

            print(f'{keys_tuples_set_copy=}')

            for keypress_tuple in keys_tuples_set_copy:
                if len(keypress_tuple) > 1:
                    # Overlap
                    if debugging:
                        if all_in_key_groups:
                            grp_name = 'KEY_SEQUENCES'
                        else:
                            grp_name = 'ALL'

                        print(f'Removing {keypress_tuple} as overlap because {grp_name} already covers it.')
                    keys_tuples_set.remove(keypress_tuple)

        # If there is nothing left in ``keys_tuples_set``, then it is set to ``None``.
        if keys_tuples_set is not None and len(keys_tuples_set) == 0:
            keys_tuples_set = None

        if debugging:
            print('After removing overlap phase III:')
            print(f'  {incl_all_multi_key_seqs=}')
            print(f'  {keys_tuples_set=}')

        # ---------------------------------------------------------------------
        # Build report data.
        # ---------------------------------------------------------------------
        self._build_report_data(
                packages,
                include_key_name_set,
                keys_tuples_set,
                limit_to_context,
                incl_all_multi_key_seqs
                )

    def _is_list_tuple_or_set(self, obj) -> bool:
        """ Is passed class a list, set or tuple? """
        T = type(obj)
        return (( T == list or T == tuple or T == set ))

    def _build_report_data(self,
            packages               : Optional[Set[str]],
            include_key_name_set   : Optional[Set[str]],
            keys_tuples_set        : Optional[Set[Tuple[str]]],
            limit_to_context       : bool,
            incl_all_multi_key_seqs: bool
            ):
        """
        Build report data required by the report dictated by the 3 arguments.
        This function only gathers information needed for the report.

        Output:
            global mdictByMainKey
            global mdictByKeySquence

        Each of the parameters are part of enabling JSON key binding objects
        to be rejected quickly, i.e. NOT included in the input data, so that
        what is left in the INPUT data is exactly what the user requested.


        :param packages:    Optional:  Set of packages to limit data to;
                            ``None`` == no limits on packages.

        :param include_key_name_set:
                            Optional:  Set against which to compare key names when
                            keypress count == 1, to accept or reject key bindings
                            being read; ``None`` == no limits on key bindings.

        :param keys_tuples_set:
                            Optional:  Set of keypress tuples against which to
                            compare individual JSON key binding objects.  If the
                            keypress tuple is a match, then it is included in the
                            input data.  VITAL:  it's vital that `keys_tuples_set`
                            contains TUPLES since tuples can use operators like
                            `==`, `!=` and `in`!  ``None`` == no specific
                            keypress/keypress sequences are added.

        :param limit_to_context:
                            Exclude key bindings that don't apply to current context?

        :param incl_all_multi_key_seqs:
                            Whether to accept all keypress sequences (i.e. JSON
                            key-binding "keys" list values that have more than
                            one keypress string in them).

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
        debugging = self._debugging_filtering_stage_i
        if debugging:
            print(f'In _build_report_data()')
            print(f'  {packages=}')
            print(f'  {include_key_name_set=}')
            print(f'  {keys_tuples_set=}')
            print(f'  {limit_to_context=}')
            print(f'  {incl_all_multi_key_seqs=}')

        # Start fresh.
        self._build_empty_main_key_dict()
        self._build_empty_key_seq_dict()

        # Loop through list of .sublime-keymap files in keymap-load order.
        keymap_paths = sublime.find_resources('*.sublime-keymap')

        # Refresh `self.view` before the outer loop starts.
        if limit_to_context:
            self.view = sublime.active_window().active_view()
        else:
            self.view = None

        # For each `.sublime-keymap` file...
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
                if debugging:
                    print(f'  Excluding package:  [{pkg_name}].')
                continue

            if debugging:
                print(f'  Including package:  [{pkg_name}].')

            # -----------------------------------------------------------------
            # If platform-specific `.sublime-keymap` file, exclude if not
            # current platform.
            # -----------------------------------------------------------------
            if 'Default (' in file_name:
                # Is a platform-specific key binding.
                if platform_name_w_parens not in file_name:
                    if debugging:
                        match = platform_name_from_file_name_re.search(file_name)
                        if match:
                            lsPlatformName = match[1]
                            print(f'  Not a platform match:  {lsPlatformName} != {platform_name}.')
                        else:
                            print(f'  Not a platform match:  {file_name}.')
                    continue

            if debugging:
                print(f'  Using {file_name}.')

            # -----------------------------------------------------------------
            # ``.sublime-keymap`` file is accepted.  Next stage.
            # -----------------------------------------------------------------
            self._conditionally_add_bindings_from_keymap(
                    path,
                    pkg_name,
                    file_name,
                    include_key_name_set,
                    keys_tuples_set,
                    incl_all_multi_key_seqs,
                    limit_to_context
                    )

    def _build_empty_main_key_dict(self):
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
        debugging = self._debugging_building_main_key_dict
        if debugging:
            print('In _build_empty_main_key_dict()')

        self.mdictByMainKey = {}

        for key_name in all_key_names:
            empty_list = [None] * 8
            self.mdictByMainKey[key_name] = empty_list

        # if debugging:
        #     print('  Empty by-main-key dict:')
        #     print(repr(self.mdictByMainKey))

    def _build_empty_key_seq_dict(self):
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
        debugging = self._debugging_building_key_seq_dict
        if debugging:
            print('In _build_empty_key_seq_dict()')

        self.mdictByKeySquence = {}

    def _conditionally_add_bindings_from_keymap(self,
            path                   : str,
            pkg_name               : str,
            file_name              : str,
            include_key_name_set   : Optional[Set[str]],
            keys_tuples_set        : Optional[Set[Tuple[str]]],
            incl_all_multi_key_seqs: bool,
            limit_to_context       : bool
            ):
        """
        Add key bindings from ``path``, that are included in these args:

        - include_key_name_set   : Optional[Set[str]],
        - keys_tuples_set        : Optional[Set[Tuple[str]]],
        - incl_all_multi_key_seqs: bool,
        - limit_to_scope         : bool


        :param path:            Packages path to .sublime-keymap file
        :param pkg_name:        Name of package (extracted by caller and used here)
        :param file_name:       .sublime-keymap file name without path.

        :param include_key_name_set:
                                Optional:  Set against which to compare key
                                names when keypress count == 1, to accept or
                                reject key bindings being read; ``None`` == no
                                limits on key bindings.

        :param keys_tuples_set: Optional:  Set of keypress tuples against which
                                to compare individual JSON key binding objects.
                                If the keypress tuple is a match, then it is
                                included in the input data. ``None`` == no
                                specific keypress/keypress sequences are added.

        :param incl_all_multi_key_seqs:
                                Whether to accept all keypress sequences
                                (i.e. JSON key-binding "keys" list values that
                                have more than one keypress string in them).

        :param limit_to_context:  Optional:  ``view is not None`` means "exclude key
                                bindings that don't apply to current context".
        """
        debugging = self._debugging_filtering_stage_ii
        if debugging:
            print(f'In _conditionally_add_bindings_from_keymap()')
            print(f'  {path=}')
            print(f'  {include_key_name_set=}')
            print(f'  {keys_tuples_set=}')
            print(f'  {incl_all_multi_key_seqs=}')
            print(f'  {limit_to_context=}')

        keymap_resource_str = sublime.load_resource(path)
        decoded_key_bindings = sublime.decode_value(keymap_resource_str)

        for decoded_binding in decoded_key_bindings:
            # -------------------------------------------------------------
            # First, look for reasons to exclude key binding.
            #
            # VITAL:  it's vital that `keypress_tuple_bep` is a TUPLE and
            # not a list.  Reason:  to be used in membership tests below.
            # -------------------------------------------------------------
            keypress_tuple_bep = tuple(decoded_binding['keys'])
            keypress_count_bep = len(keypress_tuple_bep)

            if keypress_count_bep == 1:
                # ---------------------------------------------------------
                # 1 keypress:  the most common execution branch.
                #
                # Exclude if not in either of:
                # - ``include_key_name_set`` or
                # - ``keys_tuples_set``.
                #
                # VITAL:  it's vital that `keys_tuples_set` contains TUPLES
                # since tuples can use operators like `==`, `!=` and `in`!
                # ---------------------------------------------------------
                keypress_str = keypress_tuple_bep[0]
                key_name, mod_code = main_key_and_modifier_code(keypress_str)

                is_in_keys_tuples_set = ((
                            keys_tuples_set is not None
                        and len(keys_tuples_set) > 0
                        and keypress_tuple_bep in keys_tuples_set
                        ))

                if not is_in_keys_tuples_set:
                    if include_key_name_set:
                        if key_name not in include_key_name_set:
                            # This should be excluded UNLESS its main key
                            # is in `include_key_name_set`.
                            if debugging:
                                print(f'  Excluding {keypress_tuple_bep} because:\n'
                                        f'    - that key_name was neither in `key_names` nor `key_groups`, and\n'
                                        f'    - that keypress was not in `keys_list`.'
                                        )
                            continue
                    else:
                        # Is neither in ``key_set`` nor ``include_key_name_set``.
                        if debugging:
                            print(f'  Excluding {keypress_tuple_bep} because:\n'
                                    f'    - that key_name was neither in `key_names` nor `key_groups`, and\n'
                                    f'    - that keypress was not in `keys_list`.'
                                    )
                        continue

            elif keypress_count_bep > 1:
                # ---------------------------------------------------------
                # 2+ keypresses
                #
                # Exclude if not incl_all_multi_key_seqs and not in ``keys_tuples_set``.
                # ---------------------------------------------------------
                if not incl_all_multi_key_seqs:
                    if keys_tuples_set:
                        # Exclude if not in ``keys_tuples_set``.
                        if keypress_tuple_bep not in keys_tuples_set:
                            if debugging:
                                print(f'  Excluding {keypress_tuple_bep} because:\n'
                                        f'    - KEY_SEQUENCES was not in `key_groups`,\n'
                                        f'    - that keypress sequence was not in `keys_list`.'
                                        )
                            continue
                    else:
                        # ``keys_tuples_set`` not present, exclude.
                        if debugging:
                            print(f'  Excluding {keypress_tuple_bep} because:\n'
                                    f'    - KEY_SEQUENCES was not in `key_groups`, and\n'
                                    f'    - that keypress sequence was not in `keys_list`.'
                                    )
                        continue

            else:
                # ---------------------------------------------------------
                # 0 keypresses (error condition).
                # This is an error the user needs to fix, so report it.
                # ---------------------------------------------------------
                print(f'{core.package_name} Error:  Cannot include JSON key binding with empty "keys" entry!\n'
                        f'  {keypress_tuple_bep}'
                        )
                continue

            # -------------------------------------------------------------
            # Instantiate binding.  This "hooks it up" with context query
            # apparatus in case it is needed below.
            # -------------------------------------------------------------
            binding = ReportKeyBinding(decoded_binding, pkg_name, file_name)

            # -------------------------------------------------------------
            # Exclude if caller requested `limit_to_context`, and
            # key-binding context doesn't match current context.
            # -------------------------------------------------------------
            if limit_to_context and binding.context:
                if not binding.context.query(self.view):
                    continue

            # -------------------------------------------------------------
            # When execution arrives here, it's okay to add.
            # -------------------------------------------------------------
            if keypress_count_bep > 1:
                self._add_binding_to_key_seq_dict(binding)
            else:
                self._add_binding_to_main_key_dict(binding, key_name, mod_code)

    def _add_binding_to_key_seq_dict(self, rpt_binding: ReportKeyBinding):
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
        assert rpt_binding.keypress_count() > 1, f'Number of elements in `keys` expected > 1, got {rpt_binding.keypress_count()}!'
        debugging = self._debugging_building_key_seq_dict
        if debugging:
            print('In _add_binding_to_key_seq_dict()...')
            print(f'  rpt_binding={rpt_binding.format_binding(1)}')

        keys_tuple = rpt_binding.keys_as_tuple()

        if keys_tuple not in self.mdictByKeySquence:
            # Lazy creation.
            self.mdictByKeySquence[keys_tuple] = []

        binding_list = self.mdictByKeySquence[keys_tuple]
        binding_list.append(rpt_binding)
        if debugging:
            print(f'  Added rpt_binding for {keys_tuple}.')

    def _add_binding_to_main_key_dict(self, rpt_binding: ReportKeyBinding, key_name: str, key_mod_code: int):
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
        debugging = self._debugging_building_main_key_dict
        if debugging:
            print('In _add_binding_to_main_key_dict()...')
            print(f'  {key_name=}')
            print(f'  {key_mod_code=}')
            print(f'  rpt_binding={rpt_binding.format_binding(1)}')

        if rpt_binding.keypress_count() != 1:
            raise AssertionError(f'Number of elements in `keys` expected 1, got {rpt_binding.keypress_count()}!')
        if key_name not in self.mdictByMainKey:
            raise AssertionError(f'  ERROR!  Found key name [{key_name}] not in mdictByMainKey.')

        # Here we know mdictByMainKey[key_name] exists.
        by_main_key_item = self.mdictByMainKey[key_name]
        key_binding_list = by_main_key_item[key_mod_code]

        if key_binding_list is None:
            # Lazy list creation
            key_binding_list = []
            by_main_key_item[key_mod_code] = key_binding_list

        key_binding_list.append(rpt_binding)
        if debugging:
            keypress_str = rpt_binding.keys()[0]
            print(f'  Added [{keypress_str}] rpt_binding to item [{key_mod_code}].')
