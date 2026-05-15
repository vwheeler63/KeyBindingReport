"""************************************************************************
Key-Binding Output
==================

This module is tightly paired with the ``data.py`` module, understands the
structure of the data that it built, and navigates it to produce the requested
output content.

Usage:

    See ``report.py`` for an example.


output Terminology
=============================

term
    definition

term
    definition


output Design
========================

A.  There is a concept of a KeyBindingOutput object.

    1.  It has:
        +   its own copy of the gathered key-binding data to generate
            any number of reports.
    2.  It can be asked:
        +   main_key_table
            +   returns content of gathered main-key binding data as a table
            +   ...
        +   key_sequence_table
            +   returns content of gathered key-sequence binding data as a table
            +   ...
        +   ...
            +   ...
            +   ...
    3.  It can be requested to change output objects as follows:
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...
        +   ...
            +   ...
            +   ...


KeyBindingOutput Data Flow
==========================

key-binding input data is received at instantiation of ``KeyBindingOutput``.

From that point onward, any number of reports can be generated on it.

All input data goes away when the last reference to the created
``KeyBindingOutput`` object is disposed of or goes out of scope.



@version  Current revision:  @(#) v1.0  22-Apr-2026 15:54
@version  1.0  22-Apr-2026 15:54  vw  - Created.
***************************************************************************"""

from typing import Iterable
from enum import IntFlag
from datetime import datetime

from ..lib.debug import DebugBits, is_debugging
from ..lib import ascii_table
from . import platform
from . import core
from . import data
from . import key_binding


# *************************************************************************
# Configuration
# *************************************************************************

_cfg_key_col_heading      = 'Key'
_cfg_context_col_heading  = 'Ctxt'
_cfg_command_col_heading  = 'Command'
_cfg_args_col_heading     = 'Args'



# *************************************************************************
# Constants
# *************************************************************************

class FlagBits(IntFlag):
    # Output Flags
    INCLUDE_UNBOUND_KEY_COMBINATIONS  = 0x0001  #     1
    INCLUDE_UNTRANSLATED_CONTEXTS     = 0x0002  #     2
    INCLUDE_NATURAL_LANGUAGE_CONTEXTS = 0x0004  #     4
    ADD_SOURCE_COLUMN                 = 0x0008  #     8
    ADD_COMMENTS_COLUMN               = 0x0010  #    16
    TABLE_KEY_AFTER_TABLE             = 0x0020  #    32
    INCLUDE_WINDOWS_KEY               = 0x0040  #    64
    SEPARATE_TABLES_BY_KEY_GROUPS     = 0x0080  #   128
    OUTPUT_TO_FILES                   = 0x0100  #   256
    ALL_PLATFORMS                     = 0x0200  #   512

    # Utility Bits
    ANY_CONTEXT_REQUESTED             = 0x0002 | 0x0004  # 6
    NONE                              = 0x0000  #     0
    ALL                               = 0xFFFF  # 65535
    ANY                               = 0xFFFF  # 65535



# *************************************************************************
# Data
# *************************************************************************

cmd_col_heading   = 'W'
cmd_key_name      = '⊞ Windows'
alt_col_heading   = 'A'
alt_key_name      = 'Alt'
ctrl_col_heading  = 'C'
ctrl_key_name     = 'Ctrl'
shift_col_heading = 'S'
shift_key_name    = 'Shift'
modifier_key_names_by_modifier_code_bit = {}



# *************************************************************************
# Utilities
# *************************************************************************

def show_platform_based_names():
    print(f'{cmd_col_heading   = }')
    print(f'{cmd_key_name      = }')
    print(f'{alt_col_heading   = }')
    print(f'{alt_key_name      = }')
    print(f'{ctrl_col_heading  = }')
    print(f'{ctrl_key_name     = }')
    print(f'{shift_col_heading = }')
    print(f'{shift_key_name    = }')
    print(f'{modifier_key_names_by_modifier_code_bit = }')


def update_key_names_based_on_platform(debugging: int = 0):
    if not debugging:
        debugging = is_debugging(DebugBits.PLATFORM)

    global cmd_col_heading
    global cmd_key_name
    global alt_col_heading
    global alt_key_name
    global ctrl_col_heading
    global ctrl_key_name
    global shift_col_heading
    global shift_key_name
    global modifier_key_names_by_modifier_code_bit

    # Column headings rely on platform_name.
    if platform.is_osx():
        cmd_col_heading   = 'C'
        cmd_key_name      = '⌘ Command'
        alt_col_heading   = 'O'
        alt_key_name      = '⌥ Option'
        ctrl_col_heading  = '^'
        ctrl_key_name     = 'Ctrl'
        shift_col_heading = 'S'
        shift_key_name    = 'Shift'

        modifier_key_names_by_modifier_code_bit = {
            key_binding.ModifierKeyBits.SHIFT  : 'Shift',
            key_binding.ModifierKeyBits.CTRL   : 'Ctrl',
            key_binding.ModifierKeyBits.ALT    : 'Option',
            key_binding.ModifierKeyBits.COMMAND: 'Command',
        }
    else:
        cmd_col_heading   = 'W'
        cmd_key_name      = '⊞ Windows'
        alt_col_heading   = 'A'
        alt_key_name      = 'Alt'
        ctrl_col_heading  = 'C'
        ctrl_key_name     = 'Ctrl'
        shift_col_heading = 'S'
        shift_key_name    = 'Shift'

        modifier_key_names_by_modifier_code_bit = {
            key_binding.ModifierKeyBits.SHIFT  : 'Shift',
            key_binding.ModifierKeyBits.CTRL   : 'Ctrl',
            key_binding.ModifierKeyBits.ALT    : 'Alt',
            key_binding.ModifierKeyBits.COMMAND: '⌘',
        }

    if debugging:
        show_platform_based_names()


def report_heading(title: str, note: str = '') -> str:
    timestamp = datetime.now().strftime(core.setting__timestamp_strftime_format)
    under_over_line = '*' * len(title)
    exe_platform = platform.execution_platform_name
    sim_platform = platform.platform_name
    parts = []
    parts.append('')
    parts.append(under_over_line)
    parts.append(title)
    parts.append(under_over_line)
    parts.append('')

    if sim_platform == exe_platform:
        parts.append(f'As of   :  {timestamp}')
        parts.append(f'Platform:  {exe_platform}')
    else:
        parts.append(f'As of    :  {timestamp}')
        parts.append(f'Platform :  {exe_platform}')
        parts.append(f'Simulated:  {sim_platform}')

    if note:
        parts.append('')
        parts.append('Note:')
        parts.append('')
        parts.append('    ' + note)

    return '\n'.join(parts)


def section_heading(title: str, underline_char: str) ->str:
    underline = underline_char * len(title)
    parts = []

    if underline_char == '*':
        blank_line_above_count = 3
    elif underline_char == '=':
        blank_line_above_count = 2
    elif underline_char == '-':
        blank_line_above_count = 1
    elif underline_char == '~':
        blank_line_above_count = 1
    else:
        # Not recognized, so we will assume 3.
        blank_line_above_count = 3

    for i in range(blank_line_above_count):
        parts.append('')

    parts.append(title)
    parts.append(underline)

    return '\n'.join(parts)


def include_windows_key(flags: FlagBits):
    return ((
               platform.is_osx()
            or bool(flags & FlagBits.INCLUDE_WINDOWS_KEY)
            ))



# *************************************************************************
# Function Definitions
# *************************************************************************



# *************************************************************************
# Classes
# *************************************************************************

class Footnote:
    """ Containers for key-binding table footnotes """
    __slots__ = ['key_binding', 'number', 'flags', 'format']

    def __init__(
            self,
            key_binding: key_binding.ReportKeyBinding,
            number     : int,
            flags      : FlagBits,
            format     : ascii_table.Format
            ):
        self.key_binding = key_binding
        self.number      = number
        self.flags       = flags
        self.format      = format

    def __str__(self) -> str:
        return self.formatted()

    def formatted_reference(self) -> str:
        """ Footnote reference appropriate for ``format`` """
        if self.format == ascii_table.Format.RESTRUCTUREDTEXT:
            result = f'[{self.number}]_'
        else:
            result = f'({self.number})'

        return result

    def formatted(self) -> str:
        """ Footnote content appropriate for ``format`` """
        result = ''
        binding = self.key_binding
        context = binding.smart_context()

        if context:
            raw          = bool(self.flags & FlagBits.INCLUDE_UNTRANSLATED_CONTEXTS)
            natural_lang = bool(self.flags & FlagBits.INCLUDE_NATURAL_LANGUAGE_CONTEXTS)

            footnote_str = context.formatted(
                    2,
                    raw=raw,
                    natural_language=natural_lang,
                    minimal=True
                    )

            if self.format == ascii_table.Format.RESTRUCTUREDTEXT:
                # .. [1] context for :kbd:`Alt-1`:
                # .. code-block:: json
                #
                #     "context": [
                #       { "key": "group_has_multiselect", "operator": "equal", "operand": true, "match_all": false }
                #     ]
                rst_keypress_list = binding.keypresses_human_friendly_rst_list()
                rst_keypress_str = ', '.join(rst_keypress_list)
                cmd_func_repr = binding.command_as_function_rst()
                result = (
                        f'.. [{self.number}] Context for {rst_keypress_str}:  {cmd_func_repr}\n'
                        f'.. code-block:: json\n\n{footnote_str}'
                        )
            else:
                result = f'({self.number}):\n{footnote_str}'

        return result


class KeyBindingOutput:
    """ Managers of Key-Binding Report output """
    __slots__ = ['data', 'modifier_applies_symbol', 'comments_column_width',
            'min_column_count']

    def __init__(self, data: data.KeyBindingData):
        self.data = data
        self.modifier_applies_symbol = 'x'
        self.comments_column_width = 35
        self.min_column_count = 8

    def set_modifier_applies_symbol(self, sym: str):
        """ Set modifier-applies symbol to first character in ``sym``. """
        if len(sym) == 0:
            raise AssertionError('set_modifier_applies_symbol:  `sym` must be at least 1 character long.  Got empty string.')
        self.modifier_applies_symbol = sym[0]

    def set_comments_column_width(self, width: int):
        """ Set new comments-column width. """
        self.comments_column_width = max(1, width)   # Non-negative only.

    def _heading_row(self, flags: FlagBits) -> list[str]:
        if include_windows_key(flags):
            effective_min_col_count = self.min_column_count

            result = [
                    _cfg_key_col_heading,
                    cmd_col_heading,
                    alt_col_heading,
                    ctrl_col_heading,
                    shift_col_heading,
                    _cfg_context_col_heading,
                    _cfg_command_col_heading,
                    _cfg_args_col_heading,
                    ]
        else:
            effective_min_col_count = self.min_column_count - 1

            result = [
                    _cfg_key_col_heading,
                    alt_col_heading,
                    ctrl_col_heading,
                    shift_col_heading,
                    _cfg_context_col_heading,
                    _cfg_command_col_heading,
                    _cfg_args_col_heading,
                    ]

        if len(result) != effective_min_col_count:
            raise AssertionError('KeyBindingOutput.main_key_table():  length of `result` and `min_col_count` must match.')

        if flags & FlagBits.ADD_SOURCE_COLUMN:
            result.append('Source')
        if flags & FlagBits.ADD_COMMENTS_COLUMN:
            result.append('Comments')

        return result

    def _append_rows_to_table_for_one_keypress(self,
            table               : list[list],
            main_or_2nd_key_name: str,
            mod_key_applies_tpl : tuple[str, str, str, str],
            binding_list        : list[key_binding.ReportKeyBinding],
            flags               : FlagBits,
            fmt                 : ascii_table.Format,
            footnotes           : list[Footnote],
            prev_footnote_num   : int,
            ):
        footnote_num = prev_footnote_num

        if binding_list:
            include_win_key = include_windows_key(flags)

            for binding in binding_list:
                # ---------------------------------------------------------
                # Keys
                # ---------------------------------------------------------
                if fmt == ascii_table.Format.RESTRUCTUREDTEXT:
                    tbl_key_name = key_binding.rst_escaped(main_or_2nd_key_name)
                else:
                    tbl_key_name = main_or_2nd_key_name

                row = [tbl_key_name]                    # 'f5'
                if include_win_key:
                    row.append(mod_key_applies_tpl[0])  # Windows/Command Key
                row.append(mod_key_applies_tpl[1])      # Alt
                row.append(mod_key_applies_tpl[2])      # Ctrl
                row.append(mod_key_applies_tpl[3])      # Shift

                # ---------------------------------------------------------
                # Context
                # ---------------------------------------------------------
                if binding.has_context():
                    if flags & FlagBits.ANY_CONTEXT_REQUESTED:
                        # User requested detailed context information
                        footnote_num += 1
                        footnote = Footnote(binding, footnote_num, flags, fmt)
                        footnotes.append(footnote)
                        context_ref = footnote.formatted_reference()
                    else:
                        context_ref = 'x'
                else:
                    context_ref = ' '

                row.append(context_ref)

                # ---------------------------------------------------------
                # Command
                # ---------------------------------------------------------
                row.append(binding.command())

                # ---------------------------------------------------------
                # Args
                # ---------------------------------------------------------
                if binding.has_args():
                    if fmt == ascii_table.Format.RESTRUCTUREDTEXT:
                        args_str = binding.args_rst()
                    else:
                        args_str = binding.args_json()
                else:
                    args_str = ' '

                row.append(args_str)

                # ---------------------------------------------------------
                # Remaining optional columns.
                # ---------------------------------------------------------
                if flags & FlagBits.ADD_SOURCE_COLUMN:
                    row.append(binding.source())
                if flags & FlagBits.ADD_COMMENTS_COLUMN:
                    row.append(' ' * self.comments_column_width)

                table.append(row)

        return footnote_num

    def _append_empty_row_to_table(self,
            table              : list[list],
            main_key_name      : str,
            mod_key_applies_tpl: tuple[str, str, str, str],
            flags              : FlagBits,
            fmt                : ascii_table.Format,
            ):
        include_win_key = include_windows_key(flags)

        space = ' '

        # -----------------------------------------------------------------
        # Keys
        # -----------------------------------------------------------------
        if fmt == ascii_table.Format.RESTRUCTUREDTEXT:
            tbl_key_name = key_binding.rst_escaped(main_key_name)
        else:
            tbl_key_name = main_key_name

        row = [tbl_key_name]                    # 'f5'

        if include_win_key:
            row.append(mod_key_applies_tpl[0])  # Command)

        row.append(mod_key_applies_tpl[1])      # Alt
        row.append(mod_key_applies_tpl[2])      # Ctrl
        row.append(mod_key_applies_tpl[3])      # Shift

        # -----------------------------------------------------------------
        # Context
        # -----------------------------------------------------------------
        row.append(space)                       # Context (not bound to any commands)

        # -----------------------------------------------------------------
        # Command
        # -----------------------------------------------------------------
        row.append(space)                       # Command (not bound to any commands)

        # -----------------------------------------------------------------
        # Args
        # -----------------------------------------------------------------
        row.append(space)                       # Args    (not bound to any commands)

        # -----------------------------------------------------------------
        # Remaining optional columns.
        # -----------------------------------------------------------------
        if flags & FlagBits.ADD_SOURCE_COLUMN:
            row.append(space)
        if flags & FlagBits.ADD_COMMENTS_COLUMN:
            row.append(' ' * self.comments_column_width)

        table.append(row)

    def main_key_table(self,
            flags            : FlagBits,
            fmt              : ascii_table.Format,
            prev_footnote_num: int = 0
            ) -> tuple[list[list[str]], list[Footnote], int]:
        """
        Generate and return main-key table.

        Input Data Structure:
        ---------------------
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

        Possible Columns:
        -----------------
        Key W A C S Command  Args  Context  Source  Comments

        :param flags:              OR-ed combination of FlagBits bits
        :param fmt:                needed to instantiate Footnote objects
        :param prev_footnote_num:  one-based last-footnote number;
                                     0 = first footnote has not yet been generated.

        :return:  tuple:  table, footnotes, last_footnote_num
        """
        debugging = is_debugging(DebugBits.OUTPUT)
        if debugging:
            print('In KeyBindingOutput.main_key_table()...')
            print(f'  {flags = :#011_b}')

        include_unbound_keypresses = flags & FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS
        footnote_num = prev_footnote_num
        heading_row = self._heading_row(flags)
        by_main_key_dict = self.data.mdictByMainKey

        table = [heading_row]
        footnotes = []

        for main_key_name in by_main_key_dict:
            binding_lists_by_mod_code = by_main_key_dict[main_key_name]
            key_has_bindings = any(binding_lists_by_mod_code)

            # Do not iterate through (16) sub-items when none have bindings.
            if not include_unbound_keypresses and not key_has_bindings:
                continue

            if include_unbound_keypresses:
                # Include unbound keypresses.
                for modifier_code, binding_list in enumerate(binding_lists_by_mod_code):
                    mod_key_applies_tpl = key_binding.modifier_flag_characters(modifier_code, self.modifier_applies_symbol)

                    if binding_list:
                        footnote_num = self._append_rows_to_table_for_one_keypress(
                                table,
                                main_key_name,
                                mod_key_applies_tpl,
                                binding_list,
                                flags,
                                fmt,
                                footnotes,
                                footnote_num,
                                )
                    else:
                        self._append_empty_row_to_table(
                                table,
                                main_key_name,
                                mod_key_applies_tpl,
                                flags,
                                fmt,
                                )
            else:
                # Do not include unbound keypresses.
                for modifier_code, binding_list in enumerate(binding_lists_by_mod_code):
                    if not binding_list:
                        continue

                    # Here we know ``binding_list`` contains bindings.
                    mod_key_applies_tpl = key_binding.modifier_flag_characters(modifier_code, self.modifier_applies_symbol)

                    footnote_num = self._append_rows_to_table_for_one_keypress(
                            table,
                            main_key_name,
                            mod_key_applies_tpl,
                            binding_list,
                            flags,
                            fmt,
                            footnotes,
                            footnote_num,
                            )

        return table, footnotes, footnote_num


    def main_key_tables(self,
            flags            : FlagBits,
            fmt              : ascii_table.Format,
            prev_footnote_num: int = 0
            ) -> list[    tuple[int, list[list[str]], list[Footnote], int]    ]:
        """
        Like ``main_key_table()`` only it creates a LIST of main-key tables,
        1 table per key-group occurring in the data.

        The data structure inside ``self.data.mdictByMainKey`` is already
        ordered in key-group order.  However, the logic below is simplified
        if we manager our flow of control directly from the key-group lists.

        Input Data Structure:
        ---------------------
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

        Possible Columns:
        -----------------
        Key W A C S Command  Args  Context  Source  Comments

        :param flags:              OR-ed combination of FlagBits bits
        :param fmt:                needed to instantiate Footnote objects
        :param prev_footnote_num:  one-based last-footnote number;
                                     0 = first footnote has not yet been generated.

        :return:  tuple:  table, footnotes, last_footnote_num
        """
        debugging = is_debugging(DebugBits.OUTPUT)
        if debugging:
            print('In KeyBindingOutput.main_key_tables()...')
            print(f'  {flags = :#011_b}')

        include_unbound_keypresses = flags & FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS
        footnote_num = prev_footnote_num
        heading_row = self._heading_row(flags)
        by_main_key_dict = self.data.mdictByMainKey

        table_list = []

        for key_group_idx, key_group_list in enumerate(data.key_name_groups):
            # Start new table.  Don't add headings yet until
            # we know there is going to be some content.
            table = [heading_row]
            footnotes = []

            for main_key_name in key_group_list:
                # We know ``main_key_name in by_main_key_dict`` because
                # ``key_group_list`` was used to build the empty version of
                # it at the beginning of the data gathering.
                binding_lists_by_mod_code = by_main_key_dict[main_key_name]
                key_has_bindings = any(binding_lists_by_mod_code)

                # Do not iterate through (16) sub-items when none have bindings.
                if not include_unbound_keypresses and not key_has_bindings:
                    continue

                if include_unbound_keypresses:
                    # Include unbound keypresses.
                    for modifier_code, binding_list in enumerate(binding_lists_by_mod_code):
                        mod_key_applies_tpl = key_binding.modifier_flag_characters(modifier_code, self.modifier_applies_symbol)

                        if binding_list:
                            # Now we know there is content.
                            # Heading not added yet?  Add it now.
                            if len(table) == 0:
                                table.append(heading_row)

                            footnote_num = self._append_rows_to_table_for_one_keypress(
                                    table,
                                    main_key_name,
                                    mod_key_applies_tpl,
                                    binding_list,
                                    flags,
                                    fmt,
                                    footnotes,
                                    footnote_num,
                                    )
                        else:
                            self._append_empty_row_to_table(
                                    table,
                                    main_key_name,
                                    mod_key_applies_tpl,
                                    flags,
                                    fmt,
                                    )
                else:
                    # Do not include unbound keypresses.
                    for modifier_code, binding_list in enumerate(binding_lists_by_mod_code):
                        if not binding_list:
                            continue

                        # Here we know ``binding_list`` contains bindings.
                        # Heading not added yet?  Add it now.
                        if len(table) == 0:
                            table.append(heading_row)

                        mod_key_applies_tpl = key_binding.modifier_flag_characters(modifier_code, self.modifier_applies_symbol)

                        footnote_num = self._append_rows_to_table_for_one_keypress(
                                table,
                                main_key_name,
                                mod_key_applies_tpl,
                                binding_list,
                                flags,
                                fmt,
                                footnotes,
                                footnote_num,
                                )

            # We've reached the end of a key group.
            table_list.append((key_group_idx, table, footnotes, footnote_num))

        return table_list


    def key_seq_tables(self,
            flags            : FlagBits,
            fmt              : ascii_table.Format,
            prev_footnote_num: int = 0
            ) -> list[    tuple[str, list[list[str]], list[Footnote], int]    ]:
        """
        Generate and return LIST of tuples, one per UNIQUE LEADING KEYPRESS,
        each containing:

        - leading keypress string (e.g. "ctrl+k"; can be used to form title for table)
        - table of key bindings by secondary key,
        - footnotes,
        - last_used_footnote_num (in case caller needs to append more output
          with footnotes).

        Each table generated is much like Main-Key Table except the
        `FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS` flag has no meaning
        in this report.  Only the bindings actually in the data are reported.

        Input Data Structure:
        ---------------------
        by_key_seq_dict
            ("ctrl+k", "ctrl+up"):
                [
                    ReportKeyBinding object,
                    ReportKeyBinding object,
                    ReportKeyBinding object,
                    ...
                ]

        Possible Columns:
        -----------------
        Key W A C S Command  Args  Context  Source  Comments

        :param flags:              OR-ed combination of FlagBits bits
        :param fmt:                needed to instantiate Footnote objects
        :param prev_footnote_num:  one-based last-footnote number;
                                     0 = first footnote has not yet been generated.

        :return:  list[tuple] each tuple containing:
                    (lead_keypr_str, table, footnotes, last_footnote_num)
        """
        debugging = is_debugging(DebugBits.OUTPUT)
        if debugging:
            print('In KeyBindingOutput.key_seq_tables()...')
            print(f'  {flags = :#011_b}')

        by_key_seq_dict = self.data.mdictByKeySquence

        # -----------------------------------------------------------------
        # Discover set of leading keypresses.
        # -----------------------------------------------------------------
        lead_keypr_str_set = set()

        for keypress_tuple_bep in by_key_seq_dict:
            leading_keypress_str = keypress_tuple_bep[0]
            lead_keypr_str_set.add(leading_keypress_str)

        # `lead_keypr_str_set` now contains the list of unique
        # leading keypress strings.  Example:
        # - "ctrl+j"
        # - "ctrl+k"
        # - "alt+k"
        # - "ctrl+t"

        # -----------------------------------------------------------------
        # Create top-level list.
        # -----------------------------------------------------------------
        table_list = []

        if len(lead_keypr_str_set) > 0:
            footnote_num = prev_footnote_num
            heading_row = self._heading_row(flags)

            for lead_keypr_str in sorted(lead_keypr_str_set):
                # Generate new table and new footnotes list for each
                # unique leading keypress.
                table = [heading_row]
                footnotes = []

                # ---------------------------------------------------------
                # Pass through `by_key_seq_dict` selecting only bindings
                # whose leading keypress matches `lead_keypr_str`.
                # ---------------------------------------------------------
                # `sorted()` doesn't do well for `by_key_seq_dict` because
                # it mixes the key groups up.  So we take another approach:
                # by key group in sequence.
                # ---------------------------------------------------------
                # Extract keypress_tuples by `lead_keypr_str` into a list.
                sortable_list = []
                for keypress_tuple_bep in by_key_seq_dict:
                    leading_keypress_str = keypress_tuple_bep[0]
                    if leading_keypress_str == lead_keypr_str:
                        sortable_list.append(keypress_tuple_bep)

                # Sort list by special sort routine that uses the key
                # groups and sorts by:
                # - secondary-keypress main key
                # - mod_code
                sorted_tuple_list = data.sort_keypress_tuple_list_by_secondary_key(sortable_list)

                # Finally, iterate through sorted list, pull and build
                # tables by that sequence.
                for scored_keypress_tuple_bep in sorted_tuple_list:
                    keypress_tuple = scored_keypress_tuple_bep.keypress_tuple
                    binding_list = by_key_seq_dict[keypress_tuple]

                    # Extract `mod_key_flag_char_tpl` from first binding.
                    mod_key_flag_char_tpl = key_binding.modifier_flag_characters(
                            scored_keypress_tuple_bep.mod_code,
                            self.modifier_applies_symbol
                            )

                    footnote_num = self._append_rows_to_table_for_one_keypress(
                            table,
                            scored_keypress_tuple_bep.second_main_key_name,
                            mod_key_flag_char_tpl,
                            binding_list,
                            flags,
                            fmt,
                            footnotes,
                            footnote_num,
                            )

                table_list.append((lead_keypr_str, table, footnotes, footnote_num))

        return table_list
