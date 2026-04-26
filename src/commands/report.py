from enum import IntEnum, IntFlag
from typing import Iterable, Optional
import pprint
from datetime import datetime
import sublime_plugin
import sublime
from ...lib.debug import DebugBits, is_debugging
from ...lib import ascii_table
from ...lib import output_view
from .. import core
from .. import data
from .. import output


# =========================================================================
# Configuration
# =========================================================================

_cfg_report_title = 'Key-Binding Report'


# =========================================================================
# Constants
# =========================================================================

_report_key = """Key:

  - S = Shift
  - C = Ctrl
  - A = Alt
  - (Footnote ref) prefixing command means context is shown in footnote."""


# =========================================================================
# Classes
# =========================================================================

class KeyBindingReportCommand(sublime_plugin.TextCommand):
    """ Generate Key-Binding Report in specified format. """

    def _heading(self, title: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = ['']
        parts.append(title)
        parts.append('=' * len(title))
        parts.append('')
        parts.append(f'Report generated:  {timestamp}')
        parts.append('')
        parts.append(_report_key)
        parts.append('')

        return '\n'.join(parts)

    def run(
            self            : sublime_plugin.ApplicationCommand,
            edit            : sublime.Edit,
            key_groups      : Optional[Iterable[data.KeyGroup]] = None,
            key_names       : Optional[Iterable[str]] = None,
            keypress_list   : Optional[Iterable[Iterable[str]]] = None,
            packages        : Optional[Iterable[str]] = None,
            limit_to_context: Optional[bool] = False,
            format          : ascii_table.Format = ascii_table.Format.OUTLINED,
            flags           : output.FlagBits = output.FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS
            ):
        r"""
        Generate Key-Binding Report in format `format`, limited by `packages`,
        `key_groups` and `keypress_list`.

        Precondition:   ``packages``, ``key_groups``, ``key_names`` and ``keypress_list``
                        must each be a list, set, tuple or ``None``.

        All of these arguments serve to LIMIT the output of the report.
        - packages,
        - key_names,
        - keypress_list, and
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
                            be included are in ``key_names`` and ``keypress_list``.

                            To get all individual keypresses plus all
                            multi-keypress key sequences, pass
                            ``[KeyGroup.ALL, KeyGroup.KEY_SEQUENCES]``.

        :param key_names:   List, tuple or set of key names. Meaning: report
                            on all key bindings connected to this key,
                            including all key-modifier combinations".  Only
                            honored if found in ``core.all_key_names``.
                            ``None`` or ``[]`` when key names are not limited.

        :param keypress_list:
                            List, tuple or set of "keys" (same format
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
                "key_groups"   : [1],
                "key_names"    : ["q", "w", "e", "s"],
                "keypress_list": [["ctrl+p"], ["ctrl+shift+p"], ["ctrl+k", "ctrl+u"]],
                "packages"     : ["Default"],

                // class Format(IntEnum):
                //     # Formats supported by Generator
                //     BARE             = 0
                //     OUTLINED         = 1
                //     RESTRUCTUREDTEXT = 2
                "format": 1,

                // class FlagBits(IntFlag):
                //     INCLUDE_UNBOUND_KEY_COMBINATIONS = 0b00000001  #   1
                //     INCLUDE_UNTRANSLATED_CONTEXTS    = 0b00000010  #   2
                //     INCLUDE_ENGLISH_CONTEXTS         = 0b00000100  #   4
                //     ADD_PACKAGE_COLUMN               = 0b00001000  #   8
                //     ADD_COMMENTS_COLUMN              = 0b00010000  #  16
                //
                //     NONE                             = 0b00000000  #   0
                //     ALL                              = 0b11111111  # 255
                //     ANY                              = 0b11111111  # 255
                "flags": 255,
            },
        },

        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | Description                   |packages   |key_groups   |key_names | keypress_list                          |
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
        | By specified ``keypress_list``|None or [] | None or []  |None or []|[["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]]|
        | for all Packages.             |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        """
        any_debugging = is_debugging(DebugBits.ANY)
        if any_debugging:
            print('>\n>\n>\n>')

        debugging = is_debugging(DebugBits.KEY_BINDING_REPORT)
        if debugging:
            print('In KeyBindingReportCommand.run()...')
            print(f'  {key_groups=}')
            print(f'  {key_names=}')
            print(f'  {keypress_list=}')
            print(f'  {packages=}')
            print(f'  {limit_to_context=}')
            print(f'  {format=}')
            print(f'  flags=0b{flags:08b}')

        t0 = datetime.now()
        key_data = data.KeyBindingData()

        if limit_to_context:
            view = self.view
        else:
            view = None

        key_data.generate(key_groups, key_names, keypress_list, packages, view)
        t1 = datetime.now()

        # Write verification/validation files.
        tgt_file = r'r:\by_main_key.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            # f.write(pprint.pformat(key_data.mdictByMainKey))
            f.write(pprint.pformat(key_data))
        tgt_file = r'r:\by_key_seq.txt'
        with open(tgt_file, 'w', encoding='utf-8') as f:
            # print(f'Writing to [{tgt_file}]...')
            # f.write(pprint.pformat(key_data.mdictByKeySquence))
            f.write(pprint.pformat(key_data.mdictByKeySquence))
        t2 = datetime.now()

        # Generate report.
        last_footnote_num = 0
        title   = f'{core.package_name}:  Specified Key-Bindings'
        flags   = ( #output.FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS |
                  output.FlagBits.INCLUDE_UNTRANSLATED_CONTEXTS
                | output.FlagBits.ADD_PACKAGE_COLUMN
                | output.FlagBits.ADD_FILE_COLUMN
                | output.FlagBits.ADD_COMMENTS_COLUMN
                )

        out = output.KeyBindingOutput(key_data)
        out.set_comments_column_width(60)
        mktable, last_footnote_num = out.main_key_table(flags, format, last_footnote_num)
        asc_tbl = ascii_table.AsciiTable(mktable)
        asc_tbl.set_tight_columns([True, True, True, True, False, False, False, False])
        asc_tbl.set_column_alignments(['^', '', '', '', '', '', '', ''])
        content_parts = [self._heading(title)]
        content_parts.append( asc_tbl.as_string(format) )
        content_parts.append('')
        content = '\n'.join(content_parts)

        output_view.output_to_view(
                view.window(),
                _cfg_report_title,
                content,
                current_view=view
                )
        t3 = datetime.now()

        print('Time to generate data structures: ', str(t1 - t0))
        print('Time write files                : ', str(t2 - t1))
        print('Time to generate report         : ', str(t3 - t2))
        print('Total                           : ', str(t3 - t0))
