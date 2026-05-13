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
from . import data
from .data import KeyBindingData, ModifierKeyBits
from . import core
from . smart_context import SmartContext
from ..lib.debug import DebugBits, is_debugging
from ..lib import ascii_table


# *************************************************************************
# Configuration
# *************************************************************************

flags_format_spec_hex = '014_b'
flags_format_spec_hex = '04X'



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


_rst_chars_to_escape_in_table = [
    '\\',  # Otherwise, lone '\' escapes the space ahead of it.
    '`',   # Otherwise Docutils tries to start a default interpreted-text role.
    '-',   # Otherwise Docutils interprets as a bullet
    '+',   # Otherwise Docutils interprets as a bullet
    "'",   # Otherwise Docutils converts it to an opening "smart quote" (curved).
    '"',   # Otherwise Docutils converts it to an opening "smart quote" (curved).
]



# *************************************************************************
# Data
# *************************************************************************



# *************************************************************************
# Utilities
# *************************************************************************

def report_heading(title: str, note: str = '') -> str:
    timestamp = datetime.now().strftime(core.setting__timestamp_strftime_format)
    under_over_line = '*' * len(title)
    parts = []
    parts.append('')
    parts.append(under_over_line)
    parts.append(title)
    parts.append(under_over_line)
    parts.append('')
    parts.append(f'Report generated:  {timestamp}')

    if note:
        parts.append('')
        parts.append('Note:')
        parts.append('')
        parts.append('    ' + note)

    return '\n'.join(parts)


def report_specification(
        key_groups       : Iterable[data.KeyGroup] | None,
        key_names        : Iterable[str]           | None,
        keypress_list    : Iterable[Iterable[str]] | None,
        limit_to_packages: Iterable[str]           | None,
        limit_to_context : bool,
        fmt              : ascii_table.Format,
        flags            : FlagBits,
        indent_level     : int = 0
        ) -> str:
    indent = '  ' * indent_level
    parts = []
    parts.append(f'{indent}Specification:')
    parts.append('')

    if key_groups:
        key_grp_list = []
        for kg_i in key_groups:
            key_grp_list.append(data.KeyGroup(kg_i))
        parts.append(f'{indent}    key_groups        = {key_grp_list}')
    if key_names:
        parts.append(f'{indent}    {key_names         = }')
    if keypress_list:
        parts.append(f'{indent}    {keypress_list     = }')
    if limit_to_packages:
        parts.append(f'{indent}    {limit_to_packages = }')

    parts.append(f'{indent}    {limit_to_context  = }')
    parts.append(f'{indent}    format            = {ascii_table.Format(fmt)!r}')
    parts.append(f'{indent}    flags             = 0x{flags:{flags_format_spec_hex}}')

    # Compute length of longest FlagBits enumeration name.
    longest_name_len = 0
    for enum_bit_val in FlagBits:
        if enum_bit_val != FlagBits.ALL and enum_bit_val != FlagBits.ANY:
            if flags & enum_bit_val._value_:
                name_len = len(enum_bit_val._name_)
                if name_len > longest_name_len:
                    longest_name_len = name_len

    # Report.
    for enum_bit_val in FlagBits:
        if enum_bit_val != FlagBits.ALL and enum_bit_val != FlagBits.ANY:
            if flags & enum_bit_val._value_:
                parts.append(
                        f'{indent}      - {enum_bit_val._name_:{longest_name_len}}:  '
                        f'0x{enum_bit_val._value_:{flags_format_spec_hex}}'
                        )

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


def rst_table_key_name(main_key_name: str) -> str:
    if main_key_name in _rst_chars_to_escape_in_table:
        result = '\\' + main_key_name
    else:
        result = main_key_name

    return result


def rst_table_args_str(args_str: str) -> str:
    result = args_str

    if 'res://' in result:
        # Place whole thing in a literal.
        result = '``' + result + '``'
    else:
        for c in _rst_chars_to_escape_in_table:
            if c in args_str:
                escaped_c = '\\' + c
                result = result.replace(c, escaped_c)

    return result


def include_windows_key(flags: FlagBits):
    return ((
            (data.platform == data.osx_platform_code)
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
    __slots__ = ['key_name', 'mod_code', 'number', 'context', 'flags', 'format']

    def __init__(
            self,
            key_name: str,
            mod_code: int,
            number  : int,
            context : SmartContext | None,
            flags   : FlagBits,
            format  : ascii_table.Format
            ):
        self.key_name = key_name
        self.mod_code = mod_code
        self.number   = number
        self.context  = context
        self.flags    = flags
        self.format   = format

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
        raw     = bool(self.flags & FlagBits.INCLUDE_UNTRANSLATED_CONTEXTS)
        natural_lang = bool(self.flags & FlagBits.INCLUDE_NATURAL_LANGUAGE_CONTEXTS)

        if not self.context:
            result = ''
        else:
            footnote_str = self.context.formatted(2, raw=raw, natural_language=natural_lang)

            if self.format == ascii_table.Format.RESTRUCTUREDTEXT:
                # .. [1] context for :kbd:`Alt-1`:
                # .. code-block:: json
                #
                #     "context": [
                #       { "key": "group_has_multiselect", "operator": "equal", "operand": true, "match_all": false }
                #     ]
                parts = []
                if self.mod_code:
                    bit_val = ModifierKeyBits.CTRL
                    if self.mod_code & bit_val:
                        parts.append(data.modifier_key_names_by_modifier_code_bit[bit_val])
                    bit_val = ModifierKeyBits.ALT
                    if self.mod_code & bit_val:
                        parts.append(data.modifier_key_names_by_modifier_code_bit[bit_val])
                    bit_val = ModifierKeyBits.SHIFT
                    if self.mod_code & bit_val:
                        parts.append(data.modifier_key_names_by_modifier_code_bit[bit_val])
                    bit_val = ModifierKeyBits.COMMAND
                    if self.mod_code & bit_val:
                        parts.append(data.modifier_key_names_by_modifier_code_bit[bit_val])

                parts.append(self.key_name)
                human_readable_keypr = '-'.join(parts).title()
                result = (
                        f'.. [{self.number}] Context for :kbd:`{human_readable_keypr}`:\n'
                        f'.. code-block:: json\n\n{footnote_str}'
                        )
            else:
                result = f'({self.number}):\n{footnote_str}'

        return result


class KeyBindingOutput:
    """ Managers of Key-Binding Report output """
    __slots__ = ['data', 'modifier_applies_symbol', 'comments_column_width',
            'min_column_count']

    def __init__(self, data: KeyBindingData):
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
                    'Key',
                    data.cmd_col_hdg,
                    data.alt_col_hdg,
                    data.ctrl_col_hdg,
                    data.shift_col_hdg,
                    'Ctxt',
                    'Command',
                    'Args',
                    ]
        else:
            effective_min_col_count = self.min_column_count - 1

            result = [
                    'Key',
                    data.alt_col_hdg,
                    data.ctrl_col_hdg,
                    data.shift_col_hdg,
                    'Ctxt',
                    'Command',
                    'Args',
                    ]

        if len(result) != effective_min_col_count:
            raise AssertionError('KeyBindingOutput.main_key_table():  length of `result` and `min_col_count` must match.')

        if flags & FlagBits.ADD_SOURCE_COLUMN:
            result.append('Source')
        if flags & FlagBits.ADD_COMMENTS_COLUMN:
            result.append('Comments')

        return result

    def _append_rows_to_table_for_one_keypress(self,
            table              : list[list],
            main_key_name      : str,
            modifier_code      : int,
            mod_key_applies_tpl: tuple[str, str, str, str],
            binding_list       : list[data.ReportKeyBinding],
            flags              : FlagBits,
            fmt                : ascii_table.Format,
            footnotes          : list[Footnote],
            prev_footnote_num  : int,
            ):
        footnote_num = prev_footnote_num

        if binding_list:
            include_win_key = include_windows_key(flags)

            for binding in binding_list:
                # ---------------------------------------------------------
                # Keys
                # ---------------------------------------------------------
                if fmt == ascii_table.Format.RESTRUCTUREDTEXT:
                    tbl_key_name = rst_table_key_name(main_key_name)
                else:
                    tbl_key_name = main_key_name

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
                        footnote = Footnote(main_key_name, modifier_code,
                                footnote_num, binding.smart_context(), flags, fmt)
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
                        args_str = rst_table_args_str(binding.args_json())
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
            tbl_key_name = rst_table_key_name(main_key_name)
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

            # There is no need to go through all 16 sub-items if
            # ``not key_has_bindings and not include_unbound_keypresses``.
            if not key_has_bindings and not include_unbound_keypresses:
                continue

            for modifier_code, binding_list in enumerate(binding_lists_by_mod_code):
                if not binding_list and not include_unbound_keypresses:
                    continue

                mod_key_applies_tpl = data.modifier_characters(modifier_code, self.modifier_applies_symbol)

                if binding_list:
                    footnote_num = self._append_rows_to_table_for_one_keypress(
                            table,
                            main_key_name,
                            modifier_code,
                            mod_key_applies_tpl,
                            binding_list,
                            flags,
                            fmt,
                            footnotes,
                            footnote_num,
                            )
                elif include_unbound_keypresses and key_has_bindings:
                    # TODO: review the need for ``key_has_bindings`` in condition.
                    # Does this prevent outputting say letter "b" when only "a" was
                    # asked for?  Or perhaps outputting "f1" when the F-KEY group
                    # was requested and it "f1" has no bindings?

                    # The following are all True:
                    # - `binding_list` == None,
                    # - `include_unbound_keypresses`, and
                    # - `key_has_bindings`
                    self._append_empty_row_to_table(
                            table,
                            main_key_name,
                            mod_key_applies_tpl,
                            flags,
                            fmt,
                            )
                else:
                    # No output should be generated.
                    pass

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

                # There is no need to go through all 16 sub-items if
                # ``not key_has_bindings and not include_unbound_keypresses``.
                if not key_has_bindings and not include_unbound_keypresses:
                    continue

                for modifier_code, binding_list in enumerate(binding_lists_by_mod_code):
                    if not binding_list and not include_unbound_keypresses:
                        continue

                    mod_key_applies_tpl = data.modifier_characters(modifier_code, self.modifier_applies_symbol)

                    if binding_list:
                        # Now we know there is content.
                        # Heading not added yet?  Add it now.
                        if len(table) == 0:
                            table.append(heading_row)

                        footnote_num = self._append_rows_to_table_for_one_keypress(
                                table,
                                main_key_name,
                                modifier_code,
                                mod_key_applies_tpl,
                                binding_list,
                                flags,
                                fmt,
                                footnotes,
                                footnote_num,
                                )
                    elif include_unbound_keypresses and key_has_bindings:
                        # TODO: review the need for ``key_has_bindings`` in condition.
                        # Does this prevent outputting say letter "b" when only "a" was
                        # asked for?  Or perhaps outputting "f1" when the F-KEY group
                        # was requested and it "f1" has no bindings?

                        # The following are all True:
                        # - `binding_list` == None,
                        # - `include_unbound_keypresses`, and
                        # - `key_has_bindings`
                        self._append_empty_row_to_table(
                                table,
                                main_key_name,
                                mod_key_applies_tpl,
                                flags,
                                fmt,
                                )
                    else:
                        # No output should be generated.
                        pass

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
                    mod_key_applies_tpl = data.modifier_characters(
                            scored_keypress_tuple_bep.mod_code,
                            self.modifier_applies_symbol
                            )

                    keypress_tuple = scored_keypress_tuple_bep.keypress_tuple
                    binding_list = by_key_seq_dict[keypress_tuple]

                    footnote_num = self._append_rows_to_table_for_one_keypress(
                            table,
                            scored_keypress_tuple_bep.second_main_key_name,
                            scored_keypress_tuple_bep.mod_code,
                            mod_key_applies_tpl,
                            binding_list,
                            flags,
                            fmt,
                            footnotes,
                            footnote_num,
                            )

                table_list.append((lead_keypr_str, table, footnotes, footnote_num))

        return table_list
