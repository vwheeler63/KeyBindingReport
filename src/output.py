"""************************************************************************
Key-Binding Output
==================

This module is tightly paired with the ``data.py`` module, understands the
structure of the data that it built, and navigates it to produce the requested
output content.

Usage:

    from . import output
    from ..lib import ascii_table

    key_groups       = [KeyGroup.NUMBERS]
    key_names        = ["q", "w", "a", "s"]
    keypress_list    = [["ctrl+p"], ["ctrl+shift+p"], ["ctrl+k", "ctrl+u"]]
    packages         = ["Default"]
    limit_to_context = False

    if limit_to_context:
        view = self.view   # <-- real current view, even when in a Panel or Overlay
    else:
        view = None

    key_data = KeyBindingData()
    key_data.generate(key_groups, key_names, keypress_list, packages, view)

    # ---------------------------------------------------------------------
    footnotes    = []
    footnote_num = 0
    title        = f'{core.package_name}:  Specified Key-Bindings'

    out = output.KeyBindingOutput(key_data)
    out.set_comments_column_width(60)
    mktable, footnotes, footnote_num = out.main_key_table(flags, fmt, footnotes, footnote_num)
    # pprint.pp(mktable)
    asc_tbl = ascii_table.AsciiTable(mktable)
    asc_tbl.set_tight_columns([True, True, True, True, False, False, False, False])
    asc_tbl.set_column_alignments(['^', '', '', '', '', '', '', ''])
    content_parts = [self._heading(title)]
    content_parts.append( asc_tbl.as_string(fmt) )
    content_parts.append('')

    # Insert footnotes.
    for footnote in footnotes:
        content_parts.append(footnote.formatted(flags))

    content_parts.append('')
    content = '\n'.join(content_parts)
    #
    # Keep reference to ``out`` to generate as many reports as needed.
    # ---------------------------------------------------------------------

    output_view.output_to_view(
            view.window(),
            _cfg_report_title,
            content,
            current_view=view
            )

Multiple reports can be generated from the same ``key_data``.  The input
data goes away when the last reference to ``out`` is severed.


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

from enum import IntFlag
from . import data
from .data import KeyBindingData, main_key_and_bindings_by_mod_code
from ..lib.debug import DebugBits, is_debugging
from ..lib.smart_context import SmartContext
from ..lib import ascii_table


# *************************************************************************
# Configuration
# *************************************************************************



# *************************************************************************
# Constants
# *************************************************************************



# *************************************************************************
# Data
# *************************************************************************



# *************************************************************************
# Utilities
# *************************************************************************



# *************************************************************************
# Function Definitions
# *************************************************************************

class FlagBits(IntFlag):
    # Output Flags
    INCLUDE_UNBOUND_KEY_COMBINATIONS  = 0b0000_0001  #   1
    INCLUDE_UNTRANSLATED_CONTEXTS     = 0b0000_0010  #   2
    INCLUDE_NATURAL_LANGUAGE_CONTEXTS = 0b0000_0100  #   4
    ADD_SOURCE_COLUMN                 = 0b0000_1000  #   8
    ADD_COMMENTS_COLUMN               = 0b0001_0000  #  16

    # Utility Bits
    ANY_CONTEXT_REQUESTED             = 0b0000_0010 | 0b0000_0100
    NONE                              = 0b0000_0000  #   0
    ALL                               = 0b1111_1111  # 255
    ANY                               = 0b1111_1111  # 255


class Footnote:
    """ Containers for key-binding table footnotes """
    __slots__ = ['number', 'context', 'flags', 'format']

    def __init__(
            self,
            number : int,
            context: SmartContext | None,
            flags  : FlagBits,
            format : ascii_table.Format
            ):
        self.number = number
        self.context = context
        self.flags = flags
        self.format = format

    def __str__(self) -> str:
        return self.formatted()

    def formatted_reference(self) -> str:
        """ Footnote reference appropriate for ``format`` """
        if self.format == ascii_table.Format.RESTRUCTUREDTEXT:
            result = f'([{self.number}]_)'
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
                result = f'.. [{self.number}]\n{footnote_str}'
            else:
                result = f'({self.number}):\n{footnote_str}'

        return result



# *************************************************************************
# Classes
# *************************************************************************

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
        result = [
                'Key',
                data.cmd_col_hdg,
                data.alt_col_hdg,
                data.ctrl_col_hdg,
                data.shift_col_hdg,
                'Command',
                'Args',
                'Context'
                ]

        if len(result) != self.min_column_count:
            raise AssertionError('KeyBindingOutput.main_key_table():  length of `result` and `min_col_count` must match.')

        if flags & FlagBits.ADD_SOURCE_COLUMN:
            result.append('Source')
        if flags & FlagBits.ADD_COMMENTS_COLUMN:
            result.append('Comments')

        return result

    def _append_rows_to_table_for_one_keypress(self,
            table              : list[list],
            main_key_name      : str,
            mod_key_applies_tpl: tuple[str, str, str, str],
            binding_list       : list[data.ReportKeyBinding],
            flags              : FlagBits,
            fmt                : ascii_table.Format,
            footnotes          : list[Footnote],
            prev_footnote_num  : int,
            ):
        footnote_num = prev_footnote_num

        if binding_list:
            for binding in binding_list:
                row = [''] * self.min_column_count  # Pre-allocate minimum columns
                row[0] = main_key_name  # 'f5'
                row[1] = mod_key_applies_tpl[0]  # Command
                row[2] = mod_key_applies_tpl[1]  # Alt
                row[3] = mod_key_applies_tpl[2]  # Ctrl
                row[4] = mod_key_applies_tpl[3]  # Shift
                row[5] = binding.command()
                row[6] = binding.args_json() if binding.has_args() else ' '

                if binding.has_context():
                    if flags & FlagBits.ANY_CONTEXT_REQUESTED:
                        # User requested detailed context information
                        footnote_num += 1
                        footnote = Footnote(footnote_num, binding.smart_context(), flags, fmt)
                        footnotes.append(footnote)
                        context_ref = footnote.formatted_reference()
                    else:
                        context_ref = 'x'
                else:
                    context_ref = ' '

                row[7] = context_ref

                # Remaining optional columns.
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
            ):
        space = ' '
        row = [''] * self.min_column_count  # Pre-allocate min columns
        row[0] = main_key_name           # 'f5'
        row[1] = mod_key_applies_tpl[0]  # Command
        row[2] = mod_key_applies_tpl[1]  # Alt
        row[3] = mod_key_applies_tpl[2]  # Ctrl
        row[4] = mod_key_applies_tpl[3]  # Shift
        row[5] = space                   # Command (not bound to any commands)
        row[6] = space                   # Args    (not bound to any commands)
        row[7] = space                   # Context (not bound to any commands)

        # Remaining optional columns.
        if flags & FlagBits.ADD_SOURCE_COLUMN:
            row.append(space)
        if flags & FlagBits.ADD_COMMENTS_COLUMN:
            row.append(' ' * self.comments_column_width)

        table.append(row)

    def main_key_table(self,
            flags            : FlagBits,
            fmt              : ascii_table.Format,
            footnotes        : list[Footnote]       = [],
            prev_footnote_num: int                  = 0
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
        :param footnotes:          possibly-empty list of Footnote objects
        :param prev_footnote_num:  one-based last-footnote number;
                                     0 = first footnote has not yet been generated.

        :return:  tuple:  table, footnotes, last_footnote_num
        """
        debugging = is_debugging(DebugBits.OUTPUT)
        if debugging:
            print('In KeyBindingOutput.main_key_table()...')
            print(f'  {flags =:#8b}')

        include_unbound_keypresses = flags & FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS
        footnote_num = prev_footnote_num
        heading_row = self._heading_row(flags)
        table = [heading_row]

        by_main_key_dict = self.data.mdictByMainKey

        for main_key_name in by_main_key_dict:
            binding_lists_by_mod_code = by_main_key_dict[main_key_name]
            key_has_bindings = any(binding_lists_by_mod_code)

            for modifier_code, binding_list in enumerate(binding_lists_by_mod_code):
                if not binding_list and not include_unbound_keypresses:
                    continue

                mod_key_applies_tpl = data.modifier_characters(modifier_code, self.modifier_applies_symbol)

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
                elif include_unbound_keypresses and key_has_bindings:
                    # The following are all True:
                    # - `binding_list` == None,
                    # - `include_unbound_keypresses`, and
                    # - `key_has_bindings`
                    self._append_empty_row_to_table(
                            table,
                            main_key_name,
                            mod_key_applies_tpl,
                            flags,
                            )
                else:
                    # No output should be generated.
                    pass


        return table, footnotes, footnote_num


    def key_seq_tables(self,
            flags            : FlagBits,
            fmt              : ascii_table.Format,
            footnotes        : list[Footnote]       = [],
            prev_footnote_num: int                  = 0
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
        :param footnotes:          possibly-empty list of Footnote objects
        :param prev_footnote_num:  one-based last-footnote number;
                                     0 = first footnote has not yet been generated.

        :return:  list[tuple] each tuple containing:
                    (lead_keypr_str, table, footnotes, last_footnote_num)
        """
        debugging = is_debugging(DebugBits.OUTPUT)
        if debugging:
            print('In KeyBindingOutput.key_seq_tables()...')
            print(f'  {flags =:#8b}')

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

            for lead_keypr_str in lead_keypr_str_set:
                # Generate new table and new footnotes list for each
                # unique leading keypress.
                table = [heading_row]
                footnotes = []

                # ---------------------------------------------------------
                # Pass through `by_key_seq_dict` selecting only bindings
                # whose leading keypress matches `lead_keypr_str`.
                # ---------------------------------------------------------
                for keypress_tuple_bep in by_key_seq_dict:
                    leading_keypress_str = keypress_tuple_bep[0]
                    if leading_keypress_str == lead_keypr_str:
                        # Add rows to table (and potentially add footnotes)
                        # for this binding list, using secondary keypress.
                        second_keypress_str = keypress_tuple_bep[1]

                        second_main_key_name, second_mod_code = \
                                data.main_key_and_modifier_code(second_keypress_str)

                        mod_key_applies_tpl = data.modifier_characters(
                                second_mod_code,
                                self.modifier_applies_symbol
                                )

                        binding_list = by_key_seq_dict[keypress_tuple_bep]

                        footnote_num = self._append_rows_to_table_for_one_keypress(
                                table,
                                second_main_key_name,
                                mod_key_applies_tpl,
                                binding_list,
                                flags,
                                fmt,
                                footnotes,
                                footnote_num,
                                )

                table_list.append((lead_keypr_str, table, footnotes, footnote_num))

        return table_list