"""************************************************************************
Key-Binding Report
******************

This logic is launched via the ``KeyBindingReportCommand`` command at the
end of this file.  The details of the algorithm are in the docstring for
that command.
"""
import os
from typing import Iterable
from datetime import datetime
import sublime_plugin
import sublime
from ...lib.debug import DebugBits, is_debugging
from ...lib import ascii_table
from ...lib import output_view
from .. import platform
from .. import core
from .. import data
from .. import output


# *************************************************************************
# Constants
# *************************************************************************

_report_title          = f'{core.package_name}:  Specified Key-Bindings ({{$platform}})'
_report_short_title    = 'Key-Binding Report ({$platform})'



# *************************************************************************
# Function Definitions
# *************************************************************************

def _table_key_repr(fmt: ascii_table.Format, include_win_key: bool = False) -> str:
    parts = []

    if fmt == ascii_table.Format.RESTRUCTUREDTEXT:
        """
        .. container:: table-key

            .. parsed-literal::

                **Key:**
                  A = Alt
                  C = Ctrl
                  S = Shift
        """
        indent = '    '
        indent2 = indent * 2
        parts.append('.. container:: table-key')
        parts.append('')
        parts.append(f'{indent}.. parsed-literal::')
        parts.append('')
        parts.append(f'{indent2}**Key:**')
        if include_win_key:
            parts.append(f'{indent2}     {platform.cmd_col_heading} = {platform.cmd_key_name}')
        parts.append(    f'{indent2}     {platform.alt_col_heading} = {platform.alt_key_name}')
        parts.append(    f'{indent2}     {platform.ctrl_col_heading} = {platform.ctrl_key_name}')
        parts.append(    f'{indent2}     {platform.shift_col_heading} = {platform.shift_key_name}')
        parts.append(    f'{indent2}  Ctxt = Context')
    else:
        parts.append('Key:')
        if include_win_key:
            parts.append(f'     {platform.cmd_col_heading} = {platform.cmd_key_name}')
        parts.append(    f'     {platform.alt_col_heading} = {platform.alt_key_name}')
        parts.append(    f'     {platform.ctrl_col_heading} = {platform.ctrl_key_name}')
        parts.append(    f'     {platform.shift_col_heading} = {platform.shift_key_name}')
        parts.append(     '  Ctxt = Context')

    return '\n'.join(parts)


def _key_table_and_footnotes_repr(
        key_group_idx: int,
        table        : list[list[str]],
        footnotes    : list[output.Footnote],
        fmt          : ascii_table.Format,
        flags        : data.FlagBits,
        debugging    : int,
        lead_keypr   : str | None = None,
        ) -> str:
    # if debugging:
    #     print('In _key_table_and_footnotes_repr()....')
    #     print(f'  {fmt=}')
    #     print(f'  {flags=}')
    #     print(f'  {fmt=}')
    #     print(f'  {fmt=}')

    incl_win_key = output.include_windows_key(flags)
    restructuredtext = (( fmt == ascii_table.Format.RESTRUCTUREDTEXT ))

    # ---------------------------------------------------------------------
    # Set up AsciiTable for output.
    # ---------------------------------------------------------------------
    asc_tbl = ascii_table.AsciiTable(table)

    # Prep column specs.
    # Key
    col_alignment_specs = ['^']
    tight_col_specs     = [True]

    # Windows/Command
    if incl_win_key:
        col_alignment_specs.append('')
        tight_col_specs.append(True)

    # A, C, S, Context, Cmd, Args
    col_alignment_specs.extend(['', '', '', '^', '', ''])
    tight_col_specs.extend([True, True, True, True, True, True])

    # Source
    if flags & data.FlagBits.ADD_SOURCE_COLUMN:
        col_alignment_specs.append('')
        tight_col_specs.append(False)

    # Comments
    if flags & data.FlagBits.ADD_COMMENTS_COLUMN:
        col_alignment_specs.append('')
        tight_col_specs.append(False)

    asc_tbl.set_column_alignments(col_alignment_specs)
    if fmt != ascii_table.Format.RESTRUCTUREDTEXT:
        asc_tbl.set_tight_columns(tight_col_specs)

    # ---------------------------------------------------------------------
    # Build table key and table => ``content``.
    # ---------------------------------------------------------------------
    table_key = _table_key_repr(fmt, incl_win_key)
    parts = []

    if core.setting__rst_table_container_class and restructuredtext:
        container_directive = '.. container:: ' + core.setting__rst_table_container_class
        indent = '    '
    else:
        container_directive = None
        indent = ''

    if flags & data.FlagBits.TABLE_KEY_AFTER_TABLE:
        if container_directive:
            parts.append(container_directive)
            parts.append('')
        parts.append( asc_tbl.to_string(fmt, indent) )
        parts.append('')
        parts.append(table_key)
    else:
        parts.append(table_key)
        parts.append('')
        if container_directive:
            parts.append(container_directive)
            parts.append('')
        parts.append( asc_tbl.to_string(fmt, indent) )

    # ---------------------------------------------------------------------
    # Insert footnotes => ``content``.
    # ---------------------------------------------------------------------
    for footnote in footnotes:
        if restructuredtext:
            parts.append('')
        parts.append(footnote.formatted())

    content = '\n'.join(parts)

    # ---------------------------------------------------------------------
    # Output to file(s) if requested.
    # ---------------------------------------------------------------------
    output_dir = ''
    if platform.is_windows():
        output_dir = core.setting__output_directory_for_windows
    if platform.is_linux():
        output_dir = core.setting__output_directory_for_linux
    if platform.is_osx():
        output_dir = core.setting__output_directory_for_osx

    if output_dir and (flags & data.FlagBits.OUTPUT_TO_FILES):
        key_group_file_name = data.key_group_file_names[key_group_idx]
        var_str = '{$leading_keypress}'
        if lead_keypr and var_str in key_group_file_name:
            key_group_file_name = key_group_file_name.replace(var_str, lead_keypr.replace('+', '-'))
        output_path = os.path.join(output_dir, key_group_file_name)

        try:
            if debugging:
                print(f'    Writing [{output_path}]... ', end='')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            if debugging:
                print('OK.')
        except Exception as e:
            print(f'    Writing to [{output_path}] failed: {e}')

    return content


def _key_sequence_table_title(keypress_str: str) -> str:
    # Example:  'ctrl+k'
    return 'Leading Key:  ' + keypress_str.replace('+', '-').title()


def _generate_report(
        self,
        edit             : sublime.Edit,
        key_groups       : Iterable[data.KeyGroup] | None,
        key_names        : Iterable[str]           | None,
        keypress_list    : Iterable[Iterable[str]] | None,
        limit_to_packages: Iterable[str]           | None,
        limit_to_context : bool,
        fmt              : ascii_table.Format,
        flags            : data.FlagBits,
        debugging        : int
        ) -> tuple[datetime, datetime, datetime, datetime]:
    """
    Do work for KeyBindingReportCommand, so that the command itself can
    iterate calling this repeatedly to fulfil the new ALL_PLATFORMS flag.
    """
    t0 = datetime.now()
    view = self.view
    key_data = data.KeyBindingData(fmt, flags)

    if limit_to_context:
        rpt_gen_view = self.view
    else:
        rpt_gen_view = None

    key_data.gather(key_groups, key_names, keypress_list, limit_to_packages, rpt_gen_view)
    if debugging:
        print(key_data.specification(indent_level = 1))

    t1 = datetime.now()

    # Write verification/validation files.
    # main_key_path = r'r:\by_main_key.txt'
    # key_seq_path  = r'r:\by_key_seq.txt'
    # key_data.dump_to_files(main_key_path, key_seq_path)
    t2 = datetime.now()

    # =================================================================
    # Generate report.
    # =================================================================
    last_footnote_num = 0

    if flags & data.FlagBits.INCLUDE_UNBOUND_KEYPRESSES:
        note = 'Keypresses with empty Commands are not bound.'
    else:
        note = ''

    # -----------------------------------------------------------------
    # Heading
    # -----------------------------------------------------------------
    rpt_title = _report_title.replace('{$platform}', platform.platform_name)
    content_parts = []
    content_parts.append(output.report_heading(rpt_title, note))
    content_parts.append('')
    content_parts.append(key_data.specification())

    # -----------------------------------------------------------------
    # Add Main-Key table parts.
    # -----------------------------------------------------------------
    if flags & data.FlagBits.SEPARATE_TABLES_BY_KEY_GROUPS:
        table_pkg_list = output.main_key_tables(key_data, flags, fmt, last_footnote_num)
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

                    tbl_and_footnotes = _key_table_and_footnotes_repr(
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
                output.main_key_table(key_data, flags, fmt, last_footnote_num)

        if table:
            heading = 'Single-Keypress Table'
            content_parts.append(output.section_heading(heading, '*'))
            content_parts.append('')

            tbl_and_footnotes = _key_table_and_footnotes_repr(
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
    table_pkg_list = output.key_seq_tables(key_data, flags, fmt, last_footnote_num)
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

                tbl_and_footnotes = _key_table_and_footnotes_repr(
                        data.KeyGroup.KEY_SEQUENCES,
                        table,
                        footnotes,
                        fmt,
                        flags,
                        debugging,
                        lead_keypr_str
                        )

                content_parts.append(tbl_and_footnotes)

    # This leaves `last_footnote_num` containing the last-used footnote
    # number in case we should need to add more content below.

    # -----------------------------------------------------------------
    # Finally, assemble parts into 1 string, and push to report View.
    # -----------------------------------------------------------------
    content_parts.append('')
    content = '\n'.join(content_parts)

    view_tab_heading = _report_short_title.replace('{$platform}', platform.platform_name)

    rpt_view = output_view.output_to_view(
            None,
            view_tab_heading,
            content,
            current_view=view
            )

    win = rpt_view.window()
    if win:
        win.bring_to_front()
    t3 = datetime.now()

    return t0, t1, t2, t3



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

    def run(
            self,
            edit             : sublime.Edit,
            key_groups       : Iterable[data.KeyGroup] | None = None,
            key_names        : Iterable[str]           | None = None,
            keypress_list    : Iterable[Iterable[str]] | None = None,
            limit_to_packages: Iterable[str]           | None = None,
            limit_to_context : bool = False,
            fmt              : ascii_table.Format = ascii_table.Format.OUTLINED,
            flags            : data.FlagBits = data.FlagBits.INCLUDE_UNBOUND_KEYPRESSES,
            platform_code    : str | None = None
            ):
        r"""
        Generate Key-Binding Report.

        Precondition #1:  The data type of `key_groups``, ``key_names``,
                          ``keypress_list`` and ``limit_to_packages`` must
                          each be a ``list``, ``set``, ``tuple`` or ``None``.

        Precondition #2:  If specified, ``platform_code`` must be one of
                          "windows", "linux" or "osx" (in lower case).

        These arguments ADD to the report content:
        -----------------------------------------------------------------
        - key_groups      e.g. [KeyGroup.NUMBER_KEYS],
        - key_names       e.g. ['f1', 'f2'], and
        - keypress_list   e.g. [['ctrl+k', 'ctrl+u'], ['alt+break'], ...]

        These arguments LIMIT the report content:
        -----------------------------------------------------------------
        - limit_to_packages  e.g. ['Default', 'User']
        - limit_to_context   e.g. True


        Parameters:
        ===========
        :param self:
            Command object connected to Application

        :param key_groups:
            Optional:  possibly empty list of integers from the ``KeyGroup``
            enumeration.  Keys from the specified groups will be added to the
            data gathered.  ``[KeyGroup.ALL]`` is equivalent to specifying all
            the other key groups. ``None`` or ``[]`` when not applicable.
            Default:  ``None``.

        :param key_names:
            Optional:  list of individual key names.  Each key in this list
            will be included in the data gathered, including all possible
            key-modifier combinations with this key.  Each key only has an
            impact on data gathered if it is found in
            ``data.all_key_names``. ``None`` or ``[]`` when not applicable.
            Default:  ``None``.

        :param keypress_list:
            Optional:  list of lists of "keypresses".  The inner lists have
            the same format as "keys" entries from JSON key bindings, with
            specific modifier keys.  Example:

                [["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]].

            Meaning:  include specific keypress/keypress sequences in report.
            ``None`` or ``[]`` when not applicable.  Default:  ``None``.

        :param limit_to_packages:
            Optional:  case-sensitive list of package names that the gathered
            key-binding data should be limited to.  ``None`` or ``[]`` means
            to gather data from all installed packages.  Default:
            ``None``.

        :param limit_to_context:
            True means:  exclude from data gathered:  key bindings whose
            "context" entries do not match the current circumstances
            (editing context) in the active View.  Default:  ``False``

        :param fmt:
            Output format:  integer from ``ascii_table.Format`` enumeration.
            If not a valid value from that enumeration, the default value is used.
            Default:  ``ascii_table.Format.OUTLINED``

        :param flags:
            Bitwise-OR-ed combination of ``data.FlagBits`` flag bits.
            Default:  ``data.FlagBits.INCLUDE_UNBOUND_KEYPRESSES``

        :param platform_code:
            Optional:  Platform to simulate, or None to use current platform.
            Constraint:  ``None`` (means use current platform) or one of these
            strings:  "windows", "linux" or "osx".  Default:  ``None``

        :return:  None


        Usage:
        ======

        1.  Run one of the commands that start with "KeyBindingReport:"" in the
            Command Palette.

        2.  Example running the command from a Plugin:

                args = {"key_groups": [1], "key_names": ["q", "w", "e", "s"]}
                view.run_command("key_binding_report", args)

        3.  Example Binding to a Key:

            {
                "keys": ["f4"],
                "command": "key_binding_report",
                "args": {
                    // class KeyGroup(IntEnum):
                    //     NUMBER_KEYS    =  0  # \
                    //     LETTER_KEYS    =  1  #  \
                    //     F_KEYS         =  2  #   \__ These index into ``key_name_groups``.
                    //     SYMBOL_KEYS    =  3  #   /
                    //     NAMED_KEYS     =  4  #  /
                    //     KEYPAD_KEYS    =  5  # /
                    //
                    //     FIRST          =  0  # Used in range checks, e.g. FIRST <= x <= LAST.
                    //     LAST           =  5  # Used in range checks, e.g. FIRST <= x <= LAST.
                    //
                    //     KEY_SEQUENCES  =  6  # Multiple-keypress sequences, e.g. ["ctrl+k", "ctrl+u"]
                    //     ALL            =  7  # Equivalent to specifying all groups [FIRST-LAST] + KEY_SEQUENCES.
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
                    //     INCLUDE_UNBOUND_KEYPRESSES        = 0x0001  #     1
                    //     INCLUDE_UNBOUND_KEYPRESSES_ONLY   = 0x0002  #     2
                    //     INCLUDE_UNTRANSLATED_CONTEXTS     = 0x0004  #     4
                    //     INCLUDE_NATURAL_LANGUAGE_CONTEXTS = 0x0008  #     8
                    //     ADD_SOURCE_COLUMN                 = 0x0010  #    16
                    //     ADD_COMMENTS_COLUMN               = 0x0020  #    32
                    //     TABLE_KEY_AFTER_TABLE             = 0x0040  #    64
                    //     INCLUDE_WINDOWS_KEY               = 0x0080  #   128
                    //     SEPARATE_TABLES_BY_KEY_GROUPS     = 0x0100  #   256
                    //     OUTPUT_TO_FILES                   = 0x0200  #   512
                    //     ALL_PLATFORMS                     = 0x0400  #  1024
                    //
                    //     # Utility Bits
                    //     ANY_UNBOUND_KEYPRESSES            = 0x0001 | 0x0002  #     3
                    //     ANY_CONTEXT_REQUESTED             = 0x0004 | 0x0008  #    12
                    //     NONE                              = 0x0000           #     0
                    //     ALL                               = 0xFFFF           # 65535
                    //     ANY                               = 0xFFFF           # 65535
                    //
                    "flags":  21,      // unbound,     , contexts,         , src,    ,          ,    ,           ,      ,
                    // "flags": 156,   // unbound,     , contexts, nat_lang, src,    ,          , win,           ,      ,
                    // "flags": 277,   // unbound,     , contexts,         , src,    ,          ,    , sep_tables,      ,
                    // "flags": 533,   // unbound,     , contexts,         , src,    ,          ,    ,           , files,
                    // "flags": 789,   // unbound,     , contexts,         , src,    ,          ,    , sep_tables, files,
                    // "flags": 773,   // unbound,     , contexts,         ,    ,    ,          ,    , sep_tables, files,
                    // "flags": 1797,  // unbound,     , contexts,         ,    ,    ,          ,    , sep_tables, files, all_plat
                    // "flags": 1925,  // unbound,     , contexts,         ,    ,    ,          , win, sep_tables, files, all_plat
                    // "flags": 1805,  // unbound,     , contexts, nat_lang,    ,    ,          ,    , sep_tables, files, all_plat

                    // "platform_code": "osx",
                },
            },

        See also:  ``KeyBindingReport.sublime-commands`` for more examples.


        Ways to Use This Report
        =======================

        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | Description                   |packages   |key_groups   |key_names | keypress_list                          |
        +===============================+===========+=============+==========+========================================+
        | By Package:  output all key   |["pkgname"]|    None     |   None   |    None                                |
        | bindings contained in Package |           |             |          |                                        |
        | (e.g. Default or a 3rd-party  |           |             |          |                                        |
        | Package)                      |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified key limited      |["pkgname"]|    None     |["a", ...]|    None                                |
        | to a Package:  output all     |           |             |          |                                        |
        | of key's binding(s)           |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified key:  output     |   None    |    None     |["a", ...]|    None                                |
        | that key's bindings in all    |           |             |          |                                        |
        | Packages that contain         |           |             |          |                                        |
        | bindings for that key         |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified ``KeyGroup``     |   None    |[F_KEYS, ...]|   None   |    None                                |
        | using bindings from all       |           |             |          |                                        |
        | Packages.                     |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified ``KeyGroup``     |["pkgname"]|[F_KEYS, ...]|   None   |    None                                |
        | limited to a Package.         |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        | By specified ``keypress_list``|   None    |    None     |   None   |[["ctrl+k", "ctrl+u"], ["ctrl+shift+p"]]|
        | for all Packages.             |           |             |          |                                        |
        +-------------------------------+-----------+-------------+----------+----------------------------------------+
        """
        debugging = is_debugging(DebugBits.KEY_BINDING_REPORT)
        if debugging:
            print('In KeyBindingReportCommand.run()....')

        if platform_code and platform_code not in platform.platform_names_by_code:
            raise AssertionError(f'`platform_code` must be one of {platform.platform_codes!r}.')

        if not (ascii_table.Format.FIRST <= fmt <= ascii_table.Format.LAST):
            fmt = ascii_table.Format.OUTLINED

        if flags & data.FlagBits.ALL_PLATFORMS:
            # Run once for each platform.
            platform_code_tuple = (
                    platform.windows_platform_code,
                    platform.linux_platform_code,
                    platform.osx_platform_code
                    )

            t0 = datetime.now()

            for platform_code in platform_code_tuple:
                platform.simulate_platform(platform_code)

                if debugging:
                    print(f'  Running for platform [{platform.platform_name}]....')

                t0, t1, t2, t3 = _generate_report(
                        self,
                        edit,
                        key_groups,
                        key_names,
                        keypress_list,
                        limit_to_packages,
                        limit_to_context,
                        fmt,
                        flags,
                        debugging
                        )

                if debugging:
                    print('    Time to generate data structures: ', str(t1 - t0))
                    print('    Time to write files             : ', str(t2 - t1))
                    print('    Time to generate report         : ', str(t3 - t2))
                    print('    Total                           : ', str(t3 - t0))

            # Finally, set back to normal platform again.
            platform.set_current_platform()

            if debugging:
                t4 = datetime.now()
                print('    Time to report on all platforms : ', str(t4 - t0))

        else:
            if platform_code:
                platform.simulate_platform(platform_code)

            # Just run once.
            t0, t1, t2, t3 = _generate_report(
                    self,
                    edit,
                    key_groups,
                    key_names,
                    keypress_list,
                    limit_to_packages,
                    limit_to_context,
                    fmt,
                    flags,
                    debugging
                    )

            if platform_code:
                platform.set_current_platform()

            if debugging:
                print('  Time to generate data structures: ', str(t1 - t0))
                print('  Time to write files             : ', str(t2 - t1))
                print('  Time to generate report         : ', str(t3 - t2))
                print('  Total                           : ', str(t3 - t0))
