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
    title   = 'KeyBindingReport:  Specified Key-Bindings'

    flags   = (output.FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS
            | output.FlagBits.INCLUDE_UNTRANSLATED_CONTEXTS
            | output.FlagBits.ADD_PACKAGE_COLUMN
            )

    format  = ascii_table.OUTLINED
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

from enum import IntFlag, IntEnum
from typing import List, Tuple, Set, Optional, Iterable
from ..lib.debug import DebugBits, is_debugging
from . import core
from . import data
from ..lib.debug import DebugBits, is_debugging
from ..lib import context
from ..lib import ascii_table


# =========================================================================
# Configuration
# =========================================================================



# =========================================================================
# Constants
# =========================================================================



# =========================================================================
# Data
# =========================================================================



# =========================================================================
# Utilities
# =========================================================================



# =========================================================================
# Function Definitions
# =========================================================================



# =========================================================================
# Classes
# =========================================================================

class FlagBits(IntFlag):
    # Output Flags
    INCLUDE_UNBOUND_KEY_COMBINATIONS = 0b00000001  #   1
    INCLUDE_UNTRANSLATED_CONTEXTS    = 0b00000010  #   2
    INCLUDE_ENGLISH_CONTEXTS         = 0b00000100  #   4
    ADD_PACKAGE_COLUMN               = 0b00001000  #   8
    ADD_FILE_COLUMN                  = 0b00010000  #   8
    ADD_COMMENTS_COLUMN              = 0b00100000  #  16

    # Utility Bits
    ANY_CONTEXT                      = 0b00000010 | 0b00000100
    NONE                             = 0b00000000  #   0
    ALL                              = 0b11111111  # 255
    ANY                              = 0b11111111  # 255


class KeyBindingOutput:
    """ Managers of Key-Binding Report output """
    __slots__ = ['data', 'modifier_applies_symbol', 'comments_column_width']

    def __init__(self, data: data.KeyBindingData):
        self.data = data
        self.modifier_applies_symbol = 'x'
        self.comments_column_width = 35

    def set_modifier_applies_symbol(self, sym: str):
        """ Set modifier-applies symbol to first character in ``sym``. """
        if len(sym) == 0:
            raise AssertionError('set_modifier_applies_symbol:  `sym` must be at least 1 character long.  Got empty string.')
        self.modifier_applies_symbol = sym[0]

    def set_comments_column_width(self, width: int):
        """ Set new comments-column width. """
        self.comments_column_width = max(0, width)   # Non-negative only.

    def _formated_footnote_ref(self, footnote_num: int, format: ascii_table.Format) -> str:
        """ Footnote reference appropriate for ``format`` """
        if format == ascii_table.Format.RESTRUCTUREDTEXT:
            result = f'([{footnote_num}]_)'
        else:
            result = f'({footnote_num})'

        return result

    def main_key_table(self, flags: FlagBits, format: ascii_table.Format, last_footnote_num: int) -> List[List[str]]:
        """
        Generate and return main-key table based on:

        - Contents of
          - self.data
          - self.modifier_applies_symbol
          - self.comments_column_width

        - ``flags``

        by_main_key_dict
            "a": [  <-- modifier_list
                    None,   # binding list for unmodified 'a' key
                    None,   # binding list for [Shift-a]
                    [...],  # binding list for [Ctrl-a]   <-- binding_list
                    [...],  # binding list for [Ctrl-Shift-a]
                    None,   # binding list for [Alt-a]
                    None,   # binding list for [Alt-Shift-a]
                    None,   # binding list for [Alt-Ctrl-a]
                    None,   # binding list for [Alt-Ctrl-Shift-a]
                ]

        Key S C A Command              Package            File          Comments

        :param flags:              OR-ed combination of FlagBits bits
        :param last_footnote_num:  one-based last-footnote number;
                                     0 = first footnote has not yet been generated.
        """
        debugging = is_debugging(DebugBits.OUTPUT)
        if debugging:
            print('In KeyBindingOutput.main_key_table()...')
            print(f'  0b{flags=:8b}')

        lboolInclPackage     = False
        lboolInclFile        = False
        lboolInclCommentsCol = False
        lboolContextRelevant = False
        lboolInclUnbndKeypr  = False
        col_count            = 5
        table                = []
        command_parts        = []
        footnote_contexts    = []
        empty_comments       = ' ' * self.comments_column_width
        heading_row          = ['Key', 'S', 'C', 'A', 'Command']

        if flags & FlagBits.ADD_PACKAGE_COLUMN:
            col_count += 1
            lboolInclPackage = True
            heading_row.append('Package')
        if flags & FlagBits.ADD_FILE_COLUMN:
            col_count += 1
            lboolInclFile = True
            heading_row.append('File')
        if flags & FlagBits.ADD_COMMENTS_COLUMN:
            col_count += 1
            lboolInclCommentsCol = True
            heading_row.append('Comments')
        if flags & FlagBits.ANY_CONTEXT:
            lboolContextRelevant = True
        if flags & FlagBits.INCLUDE_UNBOUND_KEY_COMBINATIONS:
            lboolInclUnbndKeypr = True

        table.append(heading_row)

        by_main_key_dict = self.data.mdictByMainKey

        for main_key in by_main_key_dict:
            modifier_list = by_main_key_dict[main_key]
            for modifier_code, binding_list in enumerate(modifier_list):
                if not binding_list and not lboolInclUnbndKeypr:
                    continue

                S, C, A = data.modifier_characters(modifier_code, self.modifier_applies_symbol)

                if binding_list:
                    for binding in binding_list:
                        # -------------------------------------------------
                        # Command Column
                        # ([3]_) command_name({'arg1': 'val1', 'arg2': 'val2'})
                        # ^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                        #   |       |
                        #   |       +-- binding.command_as_function_repr()
                        #   +-- footnote reference to context if present
                        # -------------------------------------------------
                        row = [''] * col_count  # Pre-allocate N columns
                        row[0] = main_key       # 'f5'
                        row[1] = S              # Shift
                        row[2] = C              # Ctrl
                        row[3] = A              # Alt

                        command_parts.clear()

                        if binding.has_context() and lboolContextRelevant:
                            footnote_contexts.append(binding.smart_context)
                            last_footnote_num += 1
                            footnote_ref = self._formated_footnote_ref(last_footnote_num, format)
                            command_parts.append(footnote_ref)

                        command_parts.append(binding.command_as_function_repr())
                        row[4] = ' '.join(command_parts)

                        # Remaining optional columns.
                        next_col_i = 5
                        if lboolInclPackage:
                            row[next_col_i] = binding.package_name()
                            next_col_i += 1
                        if lboolInclFile:
                            row[next_col_i] = binding.keymap_file_name()
                            next_col_i += 1
                        if lboolInclCommentsCol:
                            row[next_col_i] = empty_comments
                            next_col_i += 1

                        table.append(row)

        return table, last_footnote_num