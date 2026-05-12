import os
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
# Constants
# *************************************************************************

_report_title       = f'{core.package_name}:  Specified Key-Bindings'
_report_short_title = 'Key-Binding Report'
_flags_format_spec_bin = '014_b'
_flags_format_spec_hex = '#04x'



# *************************************************************************
# Classes
# *************************************************************************

def _table_key(fmt: ascii_table.Format, include_win_key: bool = False) -> str:
    parts = []
    win_key = (( include_win_key and data.platform != data.osx_platform_code ))

    if fmt == ascii_table.Format.RESTRUCTUREDTEXT:
        """
        **Key:**

        - A = Alt
        - C = Ctrl
        - S = Shift
        """
        parts.append('**Key:**')
        parts.append('')
        if win_key:
            parts.append(f'- {data.cmd_col_hdg} = {data.cmd_key_name}')
        parts.append(    f'- {data.alt_col_hdg} = {data.alt_key_name}')
        parts.append(    f'- {data.ctrl_col_hdg} = {data.ctrl_key_name}')
        parts.append(    f'- {data.shift_col_hdg} = {data.shift_key_name}')
    else:
        parts.append('Key:')
        if win_key:
            parts.append(f'  {data.cmd_col_hdg} = {data.cmd_key_name}')
        parts.append(    f'  {data.alt_col_hdg} = {data.alt_key_name}')
        parts.append(    f'  {data.ctrl_col_hdg} = {data.ctrl_key_name}')
        parts.append(    f'  {data.shift_col_hdg} = {data.shift_key_name}')

    return '\n'.join(parts)


def _table_and_footnotes(
        key_group_idx: int,
        table        : list[list[str]],
        footnotes    : list[output.Footnote],
        fmt          : ascii_table.Format,
        flags        : output.FlagBits,
        debugging    : int,
        lead_keypr   : str | None = None,
        ) -> str:
    if debugging:
        print('In _table_and_footnotes()....')
        print(f'  {fmt=}')
        print(f'  {flags=}')
        print(f'  {fmt=}')
        print(f'  {fmt=}')

    incl_win_key = (( data.platform == data.osx_platform_code or bool(flags & output.FlagBits.INCLUDE_WINDOWS_KEY) ))
    restructuredtext = (( fmt == ascii_table.Format.RESTRUCTUREDTEXT ))

    asc_tbl = ascii_table.AsciiTable(table)

    # Prep column specs.
    # Key
    col_alignment_specs = ['^']
    tight_col_specs     = [True]

    # Windows/Command
    if incl_win_key:
        col_alignment_specs.append('')
        tight_col_specs.append(True)

    # A, C, S, Cmd, Args, Context
    col_alignment_specs.extend(['', '', '', '', '', '^'])
    tight_col_specs.extend([True, True, True, True, True, True])

    # Source
    if flags & output.FlagBits.ADD_SOURCE_COLUMN:
        col_alignment_specs.append('')
        tight_col_specs.append(False)

    # Comments
    if flags & output.FlagBits.ADD_COMMENTS_COLUMN:
        col_alignment_specs.append('')
        tight_col_specs.append(False)

    asc_tbl.set_column_alignments(col_alignment_specs)
    if fmt != ascii_table.Format.RESTRUCTUREDTEXT:
        asc_tbl.set_tight_columns(tight_col_specs)

    table_key = _table_key(fmt, incl_win_key)
    parts = []

    if core.setting__rst_container_class and restructuredtext:
        container_directive = '.. container:: ' + core.setting__rst_container_class
        indent = '    '
    else:
        container_directive = None
        indent = ''

    if flags & output.FlagBits.TABLE_KEY_AFTER_TABLE:
        if container_directive:
            parts.append(container_directive)
            parts.append('')
        parts.append( asc_tbl.as_string(fmt, indent) )
        parts.append('')
        parts.append(table_key)
    else:
        parts.append(table_key)
        parts.append('')
        if container_directive:
            parts.append(container_directive)
            parts.append('')
        parts.append( asc_tbl.as_string(fmt, indent) )

    # Insert footnotes.
    for footnote in footnotes:
        if restructuredtext:
            parts.append('')
        parts.append(footnote.formatted())

    content = '\n'.join(parts)

    if core.setting__output_directory_windows and (flags & output.FlagBits.OUTPUT_TO_FILES):
        key_group_file_name = data.key_group_file_names[key_group_idx]
        var_str = '{$leading_keypress}'
        if lead_keypr and var_str in key_group_file_name:
            key_group_file_name = key_group_file_name.replace(var_str, lead_keypr.replace('+', '-'))
        output_path = os.path.join(core.setting__output_directory_windows, key_group_file_name)

        try:
            if debugging:
                print(f'  Attempting to open for writing [{output_path}]....')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            if debugging:
                print('  Success.')
        except Exception as e:
            print(f'Opening {output_path} for writing failed: {e}')

    return content


def _key_sequence_table_title(keypress_str: str) -> str:
    # Example:  'ctrl+k'
    return 'Leading Key:  ' + keypress_str.replace('+', '-').title()


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
                //     # Output Flags
                //     INCLUDE_UNBOUND_KEY_COMBINATIONS  = 0x0001  #     1
                //     INCLUDE_UNTRANSLATED_CONTEXTS     = 0x0002  #     2
                //     INCLUDE_NATURAL_LANGUAGE_CONTEXTS = 0x0004  #     4
                //     ADD_SOURCE_COLUMN                 = 0x0008  #     8
                //     ADD_COMMENTS_COLUMN               = 0x0010  #    16
                //     TABLE_KEY_AFTER_TABLE             = 0x0020  #    32
                //     INCLUDE_WINDOWS_KEY               = 0x0040  #    64
                //     SEPARATE_TABLES_BY_KEY_GROUPS     = 0x0080  #   128
                //     OUTPUT_TO_FILES                   = 0x0100  #   256
                //
                //     # Utility Bits
                //     ANY_CONTEXT_REQUESTED             = 0x0002 | 0x0004  # 6
                //     NONE                              = 0x0000  #     0
                //     ALL                               = 0xFFFF  # 65535
                //     ANY                               = 0xFFFF  # 65535
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
            print(f'  flags={flags:{_flags_format_spec_hex}}')

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
        main_key_path = r'r:\by_main_key.txt'
        key_seq_path  = r'r:\by_key_seq.txt'
        key_data.dump_to_files(main_key_path, key_seq_path)
        t2 = datetime.now()

        # =================================================================
        # Generate report.
        # =================================================================
        last_footnote_num = 0

        if flags & output.FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS:
            note = 'Keypresses with empty Commands are not bound.'
        else:
            note = ''

        # -----------------------------------------------------------------
        # Heading
        # -----------------------------------------------------------------
        content_parts = []
        content_parts.append(output.report_heading(_report_title, note))
        content_parts.append('')

        if key_groups:
            key_grp_list = []
            for kg_i in key_groups:
                key_grp_list.append(data.KeyGroup(kg_i))
            content_parts.append(f'key_groups        = {key_grp_list}')
        if key_names:
            content_parts.append(f'{key_names         = }')
        if keypress_list:
            content_parts.append(f'{keypress_list     = }')
        if limit_to_packages:
            content_parts.append(f'{limit_to_packages = }')

        content_parts.append(f'{limit_to_context  = }')
        content_parts.append(f'format            = {ascii_table.Format(fmt)!r}')
        content_parts.append(f'flags             = {flags:{_flags_format_spec_hex}}')

        # Compute length of longest enumeration name with bit set.
        longest_name_len = 0
        for enum_bit in output.FlagBits:
            if enum_bit != output.FlagBits.ALL and enum_bit != output.FlagBits.ANY:
                if flags & enum_bit._value_:
                    name_len = len(enum_bit._name_)
                    if name_len > longest_name_len:
                        longest_name_len = name_len

        # Report.
        for enum_bit in output.FlagBits:
            if enum_bit != output.FlagBits.ALL and enum_bit != output.FlagBits.ANY:
                if flags & enum_bit._value_:
                    content_parts.append(
                            f'  - {enum_bit._name_:{longest_name_len}}:  '
                            f'{enum_bit._value_:{_flags_format_spec_hex}}'
                            )

        # -----------------------------------------------------------------
        # Add Main-Key table parts.
        # -----------------------------------------------------------------
        out = output.KeyBindingOutput(key_data)
        out.set_comments_column_width(60)

        if flags & output.FlagBits.SEPARATE_TABLES_BY_KEY_GROUPS:
            table_pkg_list = out.main_key_tables(flags, fmt, last_footnote_num)
            #     list[tuple] (table_pkg) each tuple containing:
            #         (key_group_idx, table, footnotes, last_footnote_num)

            if table_pkg_list:
                plural_suffix = 's' if len(table_pkg_list) > 1 else ''
                heading = f'Single-Keypress Table{plural_suffix}'
                content_parts.append(output.section_heading(heading, '*'))

                for key_group_idx, table, footnotes, last_footnote_num in table_pkg_list:
                    if table:
                        heading = data.key_group_names[key_group_idx]
                        content_parts.append(output.section_heading(heading, '='))
                        content_parts.append('')

                        tbl_and_footnotes = _table_and_footnotes(
                                key_group_idx,
                                table,
                                footnotes,
                                fmt,
                                flags,
                                debugging,
                                None   # lead_keypr
                                )

                        content_parts.append(tbl_and_footnotes)

        else:
            table, footnotes, last_footnote_num = \
                    out.main_key_table(flags, fmt, last_footnote_num)

            if table:
                heading = 'Single-Keypress Table'
                content_parts.append(output.section_heading(heading, '*'))
                content_parts.append('')

                tbl_and_footnotes = _table_and_footnotes(
                        data.KeyGroup.ALL,  # All in 1 table
                        table,
                        footnotes,
                        fmt,
                        flags,
                        debugging,
                        None                # lead_keypr
                        )

                content_parts.append(tbl_and_footnotes)

        # -----------------------------------------------------------------
        # Add Key-Sequence table(s) parts.
        # -----------------------------------------------------------------
        table_pkg_list = out.key_seq_tables(flags, fmt, last_footnote_num)
        #     list[tuple] (table_pkg) each tuple containing:
        #         (lead_keypr_str, table, footnotes, last_footnote_num)

        if table_pkg_list:
            plural_suffix = 's' if len(table_pkg_list) > 1 else ''
            heading = f'Multi-Keypress Table{plural_suffix}'
            content_parts.append(output.section_heading(heading, '*'))

            for lead_keypr_str, table, footnotes, last_footnote_num in table_pkg_list:
                if table:
                    heading = _key_sequence_table_title(lead_keypr_str)
                    content_parts.append(output.section_heading(heading, '='))
                    content_parts.append('')

                    tbl_and_footnotes = _table_and_footnotes(
                            data.KeyGroup.KEY_SEQUENCES,
                            table,
                            footnotes,
                            fmt,
                            flags,
                            debugging,
                            lead_keypr_str
                            )
                    print(f'>>>>>>>>>>>>>>>>>>>>\n[{tbl_and_footnotes}]')

                    content_parts.append(tbl_and_footnotes)


        # This leaves `last_footnote_num` containing the last-used footnote
        # number in case we should need to add more content below.

        # -----------------------------------------------------------------
        # Finally, assemble parts into 1 string, and push to report View.
        # -----------------------------------------------------------------
        content = '\n'.join(content_parts)

        rpt_view = output_view.output_to_view(
                None,
                _report_short_title,
                content,
                current_view=view
                )

        rpt_view.window().bring_to_front()
        t3 = datetime.now()

        print('Time to generate data structures: ', str(t1 - t0))
        print('Time to write files             : ', str(t2 - t1))
        print('Time to generate report         : ', str(t3 - t2))
        print('Total                           : ', str(t3 - t0))
