from typing import Iterable
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


# *************************************************************************
# Configuration
# *************************************************************************

_cfg_report_title = 'Key-Binding Report'


# *************************************************************************
# Constants
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class KeyBindingReportCommand(sublime_plugin.TextCommand):
    """
    Generate Key-Binding Report in specified format.

    Inheriting from TextCommand is needed because this is the only
    way to get Views that may not be part of a Sheet, but may
    instead be part of the UI (e.g. Find textbox).  This is needed
    to feed into the context-query engine when the user has called
    the Command with ``limit_to_context == True``, in which case
    the context of the View received is what is used.
    """

    def _table_key(self) -> str:
        parts = []
        parts.append('Key:')
        parts.append(f'  {data.cmd_col_hdg} = {data.cmd_key_name}')
        parts.append(f'  {data.alt_col_hdg} = {data.alt_key_name}')
        parts.append(f'  {data.ctrl_col_hdg} = {data.ctrl_key_name}')
        parts.append(f'  {data.shift_col_hdg} = {data.shift_key_name}')

        return '\n'.join(parts)

    def _key_sequence_table_title(self, keypress_str: str) -> str:
        # Example:  'ctrl+k'
        return keypress_str.replace('+', '-').title()

    def run(
            self,
            edit             : sublime.Edit,
            key_groups       : Iterable[data.KeyGroup] | None = None,
            key_names        : Iterable[str]           | None = None,
            keypress_list    : Iterable[Iterable[str]] | None = None,
            limit_to_packages: Iterable[str]           | None = None,
            limit_to_context : bool = False,
            fmt              : ascii_table.Format = ascii_table.Format.OUTLINED,
            flags            : output.FlagBits = output.FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS
            ):
        r"""
        Generate Key-Binding Report.

        Precondition:   `key_groups``, ``key_names``, ``keypress_list`` and ``limit_to_packages``
                        must each be a list, set, tuple or ``None``.

        These arguments are interpreted "additively":
        ---------------------------------------------
        - key_groups      e.g. [KeyGroup.NUMBER_KEYS],
        - key_names       e.g. ['f1', 'f2'], and
        - keypress_list   e.g. [['ctrl+k', 'ctrl+u'], ['alt+break'], ...]

        These arguments serve to LIMIT the output of the report:
        --------------------------------------------------------
        - limit_to_packages  e.g. ['Default', 'User']
        - limit_to_context   e.g. True

        Parameters:
        -----------
        :param self:        Command object connected to Application

        :param key_groups:  List of ``KeyGroup`` integers, adding keys from these
                            groups to the data gathered.  ``KeyGroup.ALL`` is
                            equivalent to specifying all the other key groups.
                            ``None`` or ``[]`` when the only keys that should
                            be included are in ``key_names`` and ``keypress_list``.

        :param key_names:   List of individual key names.  Each key in this list
                            specifies including all possible key-modifier
                            combinations with this key.  Each key only has
                            an impact on data gathered if it is found in
                            ``data.all_key_names``.
                            ``None`` or ``[]`` when not applicable.

        :param keypress_list:
                            List of "keys" (same format as "keys" elements
                            from JSON key bindings) e.g.

                                [["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]].

                            Meaning:  include key bindings with these specific
                            keypresses/keypress sequences.
                            ``None`` or ``[]`` when not applicable.

        :param limit_to_packages:
                            List of package names data should be limited to;
                            ``None`` or ``[]`` when packages are not limited.

        :param limit_to_context:
                            Do not include key bindings that do not match the
                            current context in the active View.

        :param fmt:         Which output format (ascii_table.Format)

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

                //     NUMBER_KEYS    =  0  # \
                //     LETTER_KEYS    =  1  #  \
                //     F_KEYS         =  2  #   \__ These index into ``key_name_groups``.
                //     SYMBOL_KEYS    =  3  #   /
                //     NAMED_KEYS     =  4  #  /
                //     KEYPAD_KEYS    =  5  # /
                "key_groups"   : [1],
                "key_names"    : ["q", "w", "e", "s"],
                "keypress_list": [["ctrl+p"], ["ctrl+shift+p"], ["ctrl+k", "ctrl+u"]],
                "limit_to_packages"     : ["Default"],

                // class Format(IntEnum):
                //     # Formats supported by Generator
                //     BARE             = 0
                //     OUTLINED         = 1
                //     OUTLINED_COLUMNS = 2
                //     RESTRUCTUREDTEXT = 3
                "fmt": 1,

                // class FlagBits(IntFlag):
                //     INCLUDE_UNBOUND_KEY_COMBINATIONS = 0b00000001  #   1
                //     INCLUDE_UNTRANSLATED_CONTEXTS    = 0b00000010  #   2
                //     INCLUDE_ENGLISH_CONTEXTS         = 0b00000100  #   4
                //     ADD_SOURCE_COLUMN                = 0b00001000  #   8
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
        debugging = is_debugging(DebugBits.KEY_BINDING_REPORT)
        if debugging:
            print('>\n>\n>\n>')
            print('In KeyBindingReportCommand.run()...')
            print(f'  {key_groups=}')
            print(f'  {key_names=}')
            print(f'  {keypress_list=}')
            print(f'  {limit_to_packages=}')
            print(f'  {limit_to_context=}')
            print(f'  {fmt=}')
            print(f'  flags=0b{flags:08b}')

        t0 = datetime.now()
        view = self.view
        key_data = data.KeyBindingData()

        if limit_to_context:
            rpt_gen_view = self.view
        else:
            rpt_gen_view = None

        key_data.generate(key_groups, key_names, keypress_list, limit_to_packages, rpt_gen_view)
        t1 = datetime.now()

        # TODO: rmv after testing.
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

        # =================================================================
        # Generate report.
        # =================================================================
        footnotes = []
        last_footnote_num = 0
        title = f'{core.package_name}:  Specified Key-Bindings'
        table_key = self._table_key()

        content_parts = []
        content_parts.append(output.heading(title))
        content_parts.append('')

        out = output.KeyBindingOutput(key_data)
        out.set_comments_column_width(60)

        # -----------------------------------------------------------------
        # Add Main-Key table parts.
        # -----------------------------------------------------------------
        table, footnotes, last_footnote_num = \
                out.main_key_table(flags, fmt, footnotes, last_footnote_num)

        if table:
            mk_asc_tbl = ascii_table.AsciiTable(table)
            #                                      Key    W     A     C     S    Cmd  Args  Ctxt   Src
            mk_asc_tbl.set_tight_columns(    [True, True, True, True, True, True, True, True, False])
            mk_asc_tbl.set_column_alignments([ '^',   '',   '',   '',   '',   '',   '',  '^',    ''])
            title = 'Single-Keypress Table'
            underline = '=' * len(title)
            content_parts.append('')
            content_parts.append('')
            content_parts.append(title)
            content_parts.append(underline)
            content_parts.append('')
            content_parts.append( mk_asc_tbl.as_string(fmt) )
            content_parts.append('')
            content_parts.append(table_key)
            content_parts.append('')

            # Insert footnotes.
            for footnote in footnotes:
                content_parts.append(footnote.formatted())

            content_parts.append('')

        # -----------------------------------------------------------------
        # Add Key-Sequence table(s) parts.
        # -----------------------------------------------------------------
        tuple_list = out.key_seq_tables(flags, fmt, footnotes, last_footnote_num)
        #     list[tuple] each tuple containing:
        #         (lead_keypr_str, table, footnotes, last_footnote_num)

        if tuple_list:
            plural_suffix = 's' if len(tuple_list) > 1 else ''
            title = f'Multi-Keypress Table{plural_suffix}'
            underline = '=' * len(title)
            content_parts.append('')
            content_parts.append('')
            content_parts.append(title)
            content_parts.append(underline)
            content_parts.append('')

            for pkg in tuple_list:
                lead_keypr_str, table, footnotes, last_footnote_num = pkg

                if table:
                    kseq_asc_tbl = ascii_table.AsciiTable(table)
                    #                                      Key    W     A     C     S    Cmd  Args  Ctxt   Src
                    kseq_asc_tbl.set_tight_columns(    [True, True, True, True, True, True, True, True, False])
                    kseq_asc_tbl.set_column_alignments([ '^',   '',   '',   '',   '',   '',   '',  '^',    ''])
                    title = self._key_sequence_table_title(lead_keypr_str)
                    content_parts.append('')
                    underline = '-' * len(title)
                    content_parts.append(title)
                    content_parts.append(underline)
                    content_parts.append('')
                    content_parts.append( kseq_asc_tbl.as_string(fmt) )
                    content_parts.append('')
                    content_parts.append(table_key)
                    content_parts.append('')

                    # Insert footnotes.
                    if footnotes:
                        for footnote in footnotes:
                            content_parts.append(footnote.formatted())

                        content_parts.append('')

        # This leaves `last_footnote_num` containing the last-used footnote
        # number in case we should need to add more content below.

        # -----------------------------------------------------------------
        # Finally, assemble parts into 1 string, and push to report View.
        # -----------------------------------------------------------------
        content = '\n'.join(content_parts)

        rpt_view = output_view.output_to_view(
                None,
                _cfg_report_title,
                content,
                current_view=view
                )

        rpt_view.window().bring_to_front()
        t3 = datetime.now()

        print('Time to generate data structures: ', str(t1 - t0))
        print('Time write files                : ', str(t2 - t1))
        print('Time to generate report         : ', str(t3 - t2))
        print('Total                           : ', str(t3 - t0))
