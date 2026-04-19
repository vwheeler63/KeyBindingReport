from enum import IntEnum, IntFlag
from typing import Iterable, Optional
import pprint
from datetime import datetime
import sublime_plugin
import sublime
from ...lib.ascii_table import Format, Generator
from ...lib.debug import DebugBits, is_debugging
from .. import core
from .. import data


class FlagBits(IntFlag):
    SHOW_UNBOUND_KEY_COMBINATIONS = 0b00000001  #   1
    SHOW_PACKAGE_NAME             = 0b00000010  #   2
    ADD_COMMENTS_COLUMN           = 0b00000100  #   4
    INCLUDE_UNTRANSLATED_CONTEXTS = 0b00001000  #   8
    INCLUDE_ENGLISH_CONTEXTS      = 0b00010000  #  16

    NONE                          = 0b00000000  #   0
    ALL                           = 0b11111111  # 255
    ANY                           = 0b11111111  # 255


class KeyBindingReportCommand(sublime_plugin.ApplicationCommand):
    """ Generate Key-Binding Report in specified format. """

    def run(
            self            : sublime_plugin.ApplicationCommand,
            key_groups      : Optional[Iterable[data.KeyGroup]] = None,
            key_names       : Optional[Iterable[str]] = None,
            keys_list       : Optional[Iterable[Iterable[str]]] = None,
            packages        : Optional[Iterable[str]] = None,
            limit_to_context: Optional[bool] = False,
            format          : Format   = Format.OUTLINED,
            flags           : FlagBits = FlagBits.SHOW_UNBOUND_KEY_COMBINATIONS
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
        - limit_to_context

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

        :param limit_to_context:
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

        Example Binding to a Key:

        {
            "keys": ["ctrl+alt+shift+f4"],
            "command": "key_binding_report",
            "args": {
                // class KeyGroup(IntEnum):
                //     # Non-negative values index into ``key_name_groups``.
                //     ALL            = -2  # Equivalent to specifying all groups >= 0.
                //     KEY_SEQUENCES  = -1  # Multiple-keypress sequences, e.g. ["ctrl+k", "ctrl+u"]

                //     LETTER_KEYS    =  0  # \
                //     NUMBER_KEYS    =  1  #  \
                //     F_KEYS         =  2  #   \__ These index into ``key_name_groups``.
                //     SYMBOL_KEYS    =  3  #   /
                //     NAMED_KEYS     =  4  #  /
                //     KEYPAD_KEYS    =  5  # /
                "key_groups": [1],
                "key_names": ["q", "w", "e", "s"],
                "keys_list": [["ctrl+p"], ["ctrl+shift+p"], ["ctrl+k", "ctrl+u"]],
                "packages": ["Default"],

                // class Format(IntEnum):
                //     # Formats supported by Generator
                //     BARE             = 0
                //     OUTLINED         = 1
                //     RESTRUCTUREDTEXT = 2
                "format": 1,

                // class FlagBits(IntFlag):
                //     SHOW_UNBOUND_KEY_COMBINATIONS = 0b00000001  #   1
                //     SHOW_PACKAGE_NAME             = 0b00000010  #   2
                //     ADD_COMMENTS_COLUMN           = 0b00000100  #   4
                //     INCLUDE_UNTRANSLATED_CONTEXTS = 0b00001000  #   8
                //     INCLUDE_ENGLISH_CONTEXTS      = 0b00010000  #  16
                //
                //     NONE                          = 0b00000000  #   0
                //     ALL                           = 0b11111111  # 255
                //     ANY                           = 0b11111111  # 255
                "flags": 255,
            },
        },

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
        """

        any_debugging = is_debugging(DebugBits.ANY)
        debugging = is_debugging(DebugBits.KEY_BINDING_REPORT)

        if any_debugging:
            print('>\n>\n>\n>')

        if debugging:
            print('In KeyBindingReportCommand.run()...')
            print(f'  {key_groups=}')
            print(f'  {key_names=}')
            print(f'  {keys_list=}')
            print(f'  {packages=}')
            print(f'  {limit_to_context=}')
            print(f'  {format=}')
            print(f'  flags=0b{flags:08b}')

        t0 = datetime.now()
        key_data = data.KeyBindingData()
        key_data.generate(key_groups, key_names, keys_list, packages, limit_to_context)
        t1 = datetime.now()

        tgt_file = r'r:\by_main_key.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            f.write(pprint.pformat(key_data.mdictByMainKey))
        tgt_file = r'r:\by_key_seq.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            f.write(pprint.pformat(key_data.mdictByKeySquence))
        t2 = datetime.now()

        print('Time to generate data structures: ', str(t1 - t0))
        print('Time write files                : ', str(t2 - t1))
        print('Total                           : ', str(t2 - t0))
