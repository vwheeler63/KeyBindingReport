from enum import IntEnum, IntFlag
from typing import Iterable, Optional
import pprint  # For human-readable data dumps when debugging.
from datetime import datetime
import sublime_plugin
import sublime
from ...lib.ascii_table import Format, Generator
from ...lib.debug import DebugBits, is_debugging
from .. import core
from ..core import KeyGroup, FlagBits, package_name, gdictByMainKey, gdictByKeySquence


class KeyBindingReportCommand(sublime_plugin.ApplicationCommand):
    """ Generate Key-Binding Report in specified format. """

    def _is_list_tuple_or_set(obj) -> bool:
        """ Is passed class a list, set or tuple? """
        T = type(obj)
        return (( T == list or T == tuple or T == set ))

    def run(
            self          : sublime_plugin.ApplicationCommand,
            key_groups    : Optional[Iterable[KeyGroup]] = None,
            key_names     : Optional[Iterable[str]] = None,
            keys_list     : Optional[Iterable[Iterable[str]]] = None,
            packages      : Optional[Iterable[str]] = None,
            limit_to_scope: Optional[bool] = False,
            format        : Format   = Format.OUTLINED,
            flags         : FlagBits = FlagBits.SHOW_UNBOUND_KEY_COMBINATIONS
            ):
        r"""
        Generate Key-Binding Report in format `format`, limited by `packages`,
        `key_groups` and `keys_list`.

        Precondition:   ``packages``, ``key_groups``, ``key_names`` and ``keys_list``
                        must each be a list, set, tuple or ``None``.

        All of these arguments serve to LIMIT the output of the report.
        - packages,
        - key_names,
        - keys_list, and
        - limit_to_scope

        Omit them or pass ``None`` to intentionally remove limits in that
        particular category.

        When combinations of them appear, the results are additive, in a
        logical way.  See detailed parameters description below for details.


        Parameters:
        -----------
        :param self:        Command object connected to Application

        :param key_groups:  List, tuple or set of ``KeyGroup`` integers,
                            limiting report to those key groups.
                            ``KeyGroup.ALL`` is equivalent to specifying all
                            the other key groups.

                            ``None`` or ``[]`` when the only keys that should
                            be included are in ``key_names`` and ``keys_list``.

                            To get all individual keypresses plus all
                            multi-keypress key sequences, pass
                            ``[KeyGroup.ALL, KeyGroup.KEY_SEQUENCES]``.

        :param key_names:   List, tuple or set of key names. Meaning: report
                            on all key bindings connected to this key,
                            including all key-modifier combinations".  Only
                            honored if found in ``core.all_key_names``.
                            ``None`` or ``[]`` when key names are not limited.

        :param keys_list:   List, tuple or set of "keys" (same format
                            as "keys" elements from JSON key bindings,
                            embedded in an outer list) e.g.

                                [["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]].

                            Meaning:  report on key bindings connected to
                            these specific keypresses/keypress sequences.
                            ``None`` or ``[]`` when not applicable.

        :param packages:    List, tuple or set of package names report
                            should be limited to; ``None`` or ``[]`` when
                            packages are not limited.

        :param limit_to_scope:
                            Whether to NOT include key bindings with context
                            entries that do not match the current scope.
                            When ``True``, this command fetches the current
                            scope from the active View and passes it on
                            to ``core.build_report_data()``.

        :param format:      Which output format (ascii_table.Format)

        :param flags:       Bitwise-OR-ed combination of ``FlagBits`` enumerators.

        :return:  None


        Usage:
        ------

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
            tuples so they can more efficiently have duplicates removed.

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
            ``accepted_key_name_set``.

        3.  If (accepted_key_name_set is not None and keys_list is not None),
            this indicates the user has specified a ``keys_list`` which *may*
            have overlap with ``accepted_key_name_set``.  Since the latter
            means "report on all possible key combinations for these keys",
            any keypress/keypress sequence present in ``keys_list`` which
            has one of those key names as the main key would be redundant and
            is removed from ``keys_list``.

        4.  Finally, "overlap" may occur if:

            - ``keys_list`` and ``key_groups`` were both provided and not empty,
            - it contains any multiple keypress sequences, and
            - KEY_SEQUENCES was included in ``key_groups``,

            then all such entries in ``keys_list`` would be redundant since
            their occurrence would already be covered by the KEY_SEQUENCES
            key group.


        How Resulting Args Are Prepared
        -------------------------------
        accepted_key_name_set = None

        If ``key_groups`` was provided:
            accepted_key_name_set = Unique list of accepted key
            names based on ``key_groups``.

        If ``keys_list`` was provided:
            The above conflict/overlap resolution removed anything already
            covered by other arguments.  If there is nothing left, then
            ``keys_list`` is set to ``None``.

        Now all 3 of:

        - packages,
        - accepted_key_name_set, and
        - keys_list are passed to

        ``core.build_report_data()``.


        How Resulting Args Are Processed
        --------------------------------
        See ``core.build_report_data()`` docstring for details.
        """

        debugging = is_debugging(DebugBits.KEY_BINDING_REPORT)
        if debugging:
            print('In KeyBindingReportCommand.run()...')
            print(f'  {key_groups=}')
            print(f'  {key_names=}')
            print(f'  {keys_list=}')
            print(f'  {packages=}')
            print(f'  {limit_to_scope=}')
            print(f'  {format=}')
            print(f'  flags=0b{flags:08b}')

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
        #     tuples so they can more efficiently have duplicates removed.
        # ---------------------------------------------------------------------
        if key_groups and type(key_groups) != set:
            key_groups = set(key_groups)
        if key_names and type(key_names) != set:
            key_names = set(key_names)
        if keys_list:
            # Remember:  this is a Iterable of Iterables, e.g.
            # [["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]].
            # Lists cannot be used in sets or as dictionary keys.  So we need
            # to convert its items to tuples regardless of how many there are.
            # And we need to later assume ``keys_list`` is a set.
            temp_set = set()
            for keypresses in keys_list:
                keypress_tuple = tuple(keypresses)
                temp_set.add(keypress_tuple)

            keys_list = temp_set
        if packages and type(packages) != set:
            packages = set(packages)

        # All of packages, key_groups, key_names, keys_list are now set objects.

        if debugging:
            print('After removing duplicates:')
            print(f'  {key_groups=}')
            print(f'  {key_names=}')
            print(f'  {keys_list=}')
            print(f'  {packages=}')

        # ---------------------------------------------------------------------
        # Prepare ``accepted_key_name_set`` while removing overlap from
        # ``key_groups`` and ``keys_list` if both are present, pursuant to:
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
        #     ``accepted_key_name_set``.
        # ---------------------------------------------------------------------
        accepted_key_name_set = None   # None == no limits on key-names.

        if key_groups or key_names:
            accepted_key_name_set = set()
            if key_groups:
                # Load it with key names from the specified groups.
                if KeyGroup.ALL in key_groups:
                    accepted_key_name_set.update(core.all_key_names)
                else:
                    for key_grp_idx in key_groups:
                        if key_grp_idx >= 0:
                            key_grp_list = core.key_name_groups[key_grp_idx]
                            accepted_key_name_set.update(key_grp_list)

            # Now ``accepted_key_name_set`` contains keys in ``key_groups``
            # if ``key_groups`` was specified, or is empty if not.  If not empty,
            # it gives us an intermediate list against which to check whether
            # there is any overlap in ``key_names``, in case both were specified.
            # Example ``key_names``:  ["k", "u", "f6", "enter"].
            if key_names and accepted_key_name_set:
                # Remove any overlap in ``key_names`` resulting from any items in
                # ``key_names`` that also appear in ``accepted_key_name_set``.
                key_names_copy = key_names.copy()

                for key_name in key_names_copy:
                    if key_name in accepted_key_name_set:
                        key_names.remove(key_name)

            # Finally, add any names remaining in ``key_names`` into list.
            if key_names:
                accepted_key_name_set.update(key_names)

        if debugging:
            print('After removing overlap phase I:')
            print(f'  {key_names=}')
            print(f'  {accepted_key_name_set=}')

        # -----------------------------------------------------------------
        # Remove possible overlap between ``accepted_key_name_set``
        # and ``keys_list`` if both are present, pursuant to:
        #
        # 3.  If (accepted_key_name_set is not None and keys_list is not None),
        #     this indicates the user has specified a ``keys_list`` which *may*
        #     have overlap with ``accepted_key_name_set``.  Since the latter
        #     means "report on all possible key combinations for these keys",
        #     any keypress/keypress sequence present in ``keys_list`` which
        #     has one of those key names as the main key would be redundant and
        #     is removed from ``keys_list``.
        #
        # Example:
        # [("ctrl+k", "ctrl+u"), ("ctrl+p"), ("ctrl+shift+p")]
        # -----------------------------------------------------------------
        if accepted_key_name_set and keys_list:
            keys_list_copy = keys_list.copy()

            print(f'{keys_list_copy=}')

            for keypress_tuple in keys_list_copy:
                if len(keypress_tuple) == 1:
                    keypress = keypress_tuple[0]
                    key_name, _ = core.main_key_and_modifier_code(keypress)
                    if key_name in accepted_key_name_set:
                        # Overlap
                        if debugging:
                            print(f'Removing overlap with key {key_name} in {keypress_tuple}.')
                        keys_list.remove(keypress_tuple)

        if debugging:
            print('After removing overlap phase II:')
            print(f'  {keys_list=}')
            print(f'  {accepted_key_name_set=}')

        # -----------------------------------------------------------------
        # Remove possible overlap between ``key_groups`` and ``keys_list``
        # if both are present, pursuant to:
        #
        # 4.  Finally, "overlap" may occur if:
        #
        #     - ``keys_list`` and ``key_groups`` were both provided and not empty,
        #     - it contains any multiple keypress sequences, and
        #     - KEY_SEQUENCES was included in ``key_groups``,
        #
        #     then all such entries in ``keys_list`` would be redundant since
        #     their occurrence would already be covered by the KEY_SEQUENCES
        #     key group.
        # -----------------------------------------------------------------
        accept_all_key_sequences = ((
                key_groups is not None
                and len(key_groups) > 0
                and KeyGroup.KEY_SEQUENCES in key_groups
                ))

        if keys_list and accept_all_key_sequences:
            keys_list_copy = keys_list.copy()

            print(f'{keys_list_copy=}')

            for keypress_tuple in keys_list_copy:
                if len(keypress_tuple) > 1:
                    # Overlap
                    if debugging:
                        print(f'Removing {keypress_tuple} as overlap because KEY_SEQUENCES already covers it.')
                    keys_list.remove(keypress_tuple)

        # If there is nothing left in ``keys_list``, then it is set to ``None``.
        if keys_list is not None and len(keys_list) == 0:
            keys_list = None

        if debugging:
            print('After removing overlap phase III:')
            print(f'  {accept_all_key_sequences=}')
            print(f'  {keys_list=}')

        # ---------------------------------------------------------------------
        # Build report data.
        # ---------------------------------------------------------------------
        t0 = datetime.now()
        core.build_report_data(
                packages,
                accepted_key_name_set,
                keys_list,
                limit_to_scope,
                accept_all_key_sequences
                )
        t1 = datetime.now()
        print('Time to build data structures: ', str(t1 - t0))

        # import os
        # this_dir, _ = os.path.split(__file__)
        # tgt_file = os.path.join(this_dir, 'by_main_key.txt')
        # with open(tgt_file, 'w', encoding='utf-8') as f:
        #     print(f'Writing to [{tgt_file}]...')
        #     f.write(pprint.pformat(gdictByMainKey))
        # tgt_file = os.path.join(this_dir, 'by_key_seq.txt')
        # with open(tgt_file, 'w', encoding='utf-8') as f:
        #     print(f'Writing to [{tgt_file}]...')
        #     f.write(pprint.pformat(gdictByKeySquence))

        tgt_file = r'r:\by_main_key.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            f.write(pprint.pformat(core.gdictByMainKey))
        tgt_file = r'r:\by_key_seq.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            f.write(pprint.pformat(core.gdictByKeySquence))
        t2 = datetime.now()
        print('Time write files             : ', str(t2 - t1))
        print('Total                        : ', str(t2 - t0))
