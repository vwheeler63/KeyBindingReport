from typing import List, Iterable
from enum import IntEnum


class Format(IntEnum):
    """ Formats supported by AsciiTable """
    BARE             = 0
    OUTLINED         = 1
    RESTRUCTUREDTEXT = 2


class AsciiTable():
    """
    Tables that can generate ASCII representations of themselves
    in a variety of formats.
    """
    __slots__ = ['table', 'row_count', 'column_count', 'max_column_widths', 'column_alignments']

    def __init__(self, table: List[Iterable[str]]):
        self.table = table
        self._gather_metadata()

    def __repr__(self):
        result = f'{{AsciiTable: rows={self.row_count}, cols={self.column_count}}}\n'
        for i, w in enumerate(self.max_column_widths):
            result += f'  Col {i + 1} max width: {w:>2}\n'
        return result

    def set_column_alignments(self, alignment_list: Iterable[str]):
        """
        Align Specifiers
        ----------------
        '<'  left-aligned within the available space (default for most objects)

        '>'  right-aligned within the available space (default for numbers)

        '='  Forces the padding to be placed after the sign (if any) but before the digits.
             This is used for printing fields in the form '+000000120'.  This alignment
             option is only valid for numeric types, excluding complex.  It becomes the
             default for numbers when '0' immediately precedes the field width.

        '^'  Forces the field to be centered within the available space.
        """
        if len(alignment_list) != len(self.max_column_widths):
            msg = f'`alignment_list` must have {len(self.max_column_widths)} elements.  Got {len(alignment_list)} instead.'
            raise AssertionError(msg)
        self.column_alignments = alignment_list

    def as_string(self, fmt: Format):
        """ Representation of `self` as a string """
        if fmt == Format.BARE:
            result = self._bare_string_repr()
        elif fmt == Format.OUTLINED:
            result = self._outlined_string_repr()
        elif fmt == Format.RESTRUCTUREDTEXT:
            result = self._restructuredtext_string_repr()
        else:
            result = ''

        return result

    def _gather_metadata(self):
        """ Gather information needed about `self.table` """
        self.row_count = len(self.table)
        self.column_count = 0
        self.max_column_widths = []

        for row in self.table:
            # Keep max in ``column_count`` and extend ``max_column_widths`` if needed.
            if (col_count := len(row)) > self.column_count:
                self.column_count = col_count
                while (curr_cols := len(self.max_column_widths)) < col_count:
                    self.max_column_widths.append(0)

            for i, field in enumerate(row):
                if (width := len(field)) > self.max_column_widths[i]:
                    self.max_column_widths[i] = width

        self.column_alignments = [''] * self.column_count

    def _row_separator(self, line_char: str):
        row_sep_parts = ['+']

        for max_w in self.max_column_widths:
            col_segment = line_char * (max_w + 2)
            row_sep_parts.append(col_segment)
            row_sep_parts.append('+')

        return ''.join(row_sep_parts)


    def _single_line_row_separator(self):
        return self._row_separator('-')


    def _double_line_row_separator(self):
        return self._row_separator('=')

    def _bare_string_repr(self):
        """
        Package                  Shipped   Installed   Unpacked
        Default                  [S]       [ ]         [U]
        .git                     [ ]       [ ]         [U]
        A File Icon              [ ]       [I]         [ ]
        ASP                      [S]       [ ]         [ ]
        ActionScript             [S]       [ ]         [ ]

        Default column separation == 3 spaces.
        """
        lines = []
        line_parts = []
        col_sep = '   '

        for row in self.table:
            line_parts.clear()
            last_col_idx = len(row) - 1

            for i, col in enumerate(row):
                col_repr = f'{col:{self.column_alignments[i]}{self.max_column_widths[i]}}'
                line_parts.append(col_repr)

            line = col_sep.join(line_parts)
            lines.append(line)

        return '\n'.join(lines)


    def _outlined_string_repr(self):
        """
        +------------------------+---------+-----------+----------+
        | Package                | Shipped | Installed | Unpacked |
        | Default                | [S]     | [ ]       | [U]      |
        | .git                   | [ ]     | [ ]       | [U]      |
        | A File Icon            | [ ]     | [I]       | [ ]      |
        | ASP                    | [S]     | [ ]       | [ ]      |
        | ActionScript           | [S]     | [ ]       | [ ]      |
        +------------------------+---------+-----------+----------+
        """
        lines = []
        line_parts = []
        row_sep = self._single_line_row_separator()

        lines.append(row_sep)

        for row in self.table:
            line_parts.clear()
            line_parts.append('|')

            for i, col in enumerate(row):
                col_repr = f'{col:{self.column_alignments[i]}{self.max_column_widths[i]}}'
                line_parts.append(' ')
                line_parts.append(col_repr)
                line_parts.append(' |')

            line = ''.join(line_parts)
            lines.append(line)

        lines.append(row_sep)

        return '\n'.join(lines)

    def _restructuredtext_string_repr(self):
        """
        +------------------------+---------+-----------+----------+
        | Package                | Shipped | Installed | Unpacked |
        +------------------------+---------+-----------+----------+
        | Default                | [S]     | [ ]       | [U]      |
        +------------------------+---------+-----------+----------+
        | .git                   | [ ]     | [ ]       | [U]      |
        +------------------------+---------+-----------+----------+
        | A File Icon            | [ ]     | [I]       | [ ]      |
        +------------------------+---------+-----------+----------+
        | ASP                    | [S]     | [ ]       | [ ]      |
        +------------------------+---------+-----------+----------+
        | ActionScript           | [S]     | [ ]       | [ ]      |
        +------------------------+---------+-----------+----------+
        """
        lines = []
        line_parts = []
        row_sep = self._single_line_row_separator()
        title_sep = self._double_line_row_separator()

        lines.append(row_sep)
        last_row_idx = self.row_count - 1

        for i, row in enumerate(self.table):
            line_parts.clear()
            line_parts.append('|')

            for i, col in enumerate(row):
                col_repr = f'{col:{self.column_alignments[i]}{self.max_column_widths[i]}}'
                line_parts.append(' ')
                line_parts.append(col_repr)
                line_parts.append(' |')

            line = ''.join(line_parts)
            lines.append(line)

            if i == 0:
                lines.append(title_sep)
            else:
                lines.append(row_sep)

        return '\n'.join(lines)


if __name__ == '__main__':
    # ---------------------------------------------------------------------
    # Test
    # ---------------------------------------------------------------------
    with open('tab_sep_table_test.txt', 'r', encoding='utf-8') as f:
        # Default\t[S]\t[ ]\t[U]
        content = f.read()

    lines = content.split('\n')
    rows = []

    for line in lines:
        fields = line.split('\t')
        # Trim spaces in fields.
        for i, field in enumerate(fields):
            fields[i] = field.strip()

        rows.append(fields)

    # ---------------------------------------------------------------------
    # ``rows`` is now a List[Iterable[str]] needed by ``AsciiTable``.
    # ---------------------------------------------------------------------
    table = AsciiTable(rows)
    # table.set_column_alignments(['', '^', '^', '^'])
    print(repr(table))
    print(table.as_string(Format.BARE))
    print(table.as_string(Format.OUTLINED))
    print(table.as_string(Format.RESTRUCTUREDTEXT))
