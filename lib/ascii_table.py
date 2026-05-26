from enum import IntEnum


class Format(IntEnum):
    """ Formats supported by AsciiTable """
    BARE             = 0
    OUTLINED         = 1
    OUTLINED_COLUMNS = 2
    RESTRUCTUREDTEXT = 3

    FIRST            = 0
    LAST             = 3


class AsciiTable():
    """
    Tables that can generate ASCII representations of themselves
    in a variety of formats.
    """
    __slots__ = [
            'table',
            'row_count',
            'column_count',
            'max_column_widths',
            'column_alignments',
            'tight_columns',
            'debugging'
            ]

    def __init__(self, table: list[list[str]]):
        if table is None:
            msg = '`table` must be a list of iterables elements.  Got `None` instead.'
            raise AssertionError(msg)
        self.table = table
        self.debugging = False
        self._gather_metadata()

    def __repr__(self):
        result = f'{{AsciiTable: rows={self.row_count}, cols={self.column_count}}}\n'
        for i, w in enumerate(self.max_column_widths):
            result += f'  Col {i + 1} max width: {w:>2}\n'
        return result

    def _gather_metadata(self):
        """ Gather information needed about `self.table` """
        self.row_count = len(self.table)
        self.column_count = 0
        self.max_column_widths = []

        for row in self.table:
            # Keep max in ``column_count`` and extend ``max_column_widths`` when needed.
            if (col_count := len(row)) > self.column_count:
                self.column_count = col_count
                while (len(self.max_column_widths)) < col_count:
                    self.max_column_widths.append(1)

            for i, field in enumerate(row):
                if (width := len(field)) > self.max_column_widths[i]:
                    self.max_column_widths[i] = max(1, width)

        self.column_alignments = [''] * self.column_count
        self.tight_columns = [False] * self.column_count

    def set_column_alignments(self, alignment_list: list[str]):
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

    def set_tight_columns(self, tight_col_list: list[bool]):
        """
        Set whether each column is considered "tight".

        Tight means no whitespace to the left or right of its contents.
        """
        if len(tight_col_list) != len(self.max_column_widths):
            msg = f'`tight_col_list` must have {len(self.max_column_widths)} elements.  Got {len(tight_col_list)} instead.'
            raise AssertionError(msg)
        self.tight_columns = tight_col_list

    def to_string(self, fmt: Format, indent: str = ''):
        if self.debugging:
            print(f'In {self.__class__.__name__}.to_string()....')
            print(f'  {fmt                    = }')
            print(f'  {self.row_count         = }')
            print(f'  {self.column_count      = }')
            print(f'  {self.max_column_widths = }')
            print(f'  {self.column_alignments = }')
            print(f'  {self.tight_columns     = }')

        """ Representation of `self` as a string """
        if fmt == Format.BARE:
            result = self._bare_repr(indent)
        elif fmt == Format.OUTLINED:
            result = self._outlined_repr(False, indent)
        elif fmt == Format.OUTLINED_COLUMNS:
            result = self._outlined_repr(True, indent)
        elif fmt == Format.RESTRUCTUREDTEXT:
            result = self._restructuredtext_repr(indent)
        else:
            result = ''

        return result

    def _row_separator(self, line_char: str, with_col_seps: bool = False):
        row_sep_parts = ['+']
        last_i = self.column_count - 1

        for i, max_w in enumerate(self.max_column_widths):
            if self.tight_columns[i]:
                col_segment = line_char * max_w
            else:
                col_segment = line_char * (max_w + 2)

            row_sep_parts.append(col_segment)

            if with_col_seps or i == last_i:
                row_sep_parts.append('+')
            else:
                row_sep_parts.append(line_char)

        return ''.join(row_sep_parts)

    def _single_line_row_separator(self, with_col_seps: bool = False):
        return self._row_separator('-', with_col_seps)

    def _double_line_row_separator(self, with_col_seps: bool = False):
        return self._row_separator('=', with_col_seps)

    def _bare_repr(self, indent: str):
        """
        Package                  Shipped   Installed   Unpacked
        Default                  [S]       [ ]         [U]
        .git                     [ ]       [ ]         [U]
        A File Icon              [ ]       [I]         [ ]
        ASP                      [S]       [ ]         [ ]
        ActionScript             [S]       [ ]         [ ]

        Default column separation == 3 spaces.

        Tight columns only impact this format when 2 adjacent columns
        are both "tight".
        """
        lines = []
        line_parts = []
        col_sep = '   '
        tight_col_sep = '  '

        for row in self.table:
            line_parts.clear()

            if indent:
                line_parts.append(indent)

            last_i = len(row) - 1

            for i, col in enumerate(row):
                col_repr = f'{col:{self.column_alignments[i]}{self.max_column_widths[i]}}'
                line_parts.append(col_repr)

                if i < last_i:
                    # Not last column.
                    if self.tight_columns[i]:
                        line_parts.append(tight_col_sep)
                    else:
                        line_parts.append(col_sep)

            line = ''.join(line_parts)
            lines.append(line)

        return '\n'.join(lines)


    def _outlined_repr(self, with_col_seps: bool, indent: str):
        """
        with_col_seps = False:
        +---------------------------------------------------------+
        | Package                  Shipped   Installed   Unpacked |
        | Default                  [S]       [ ]         [U]      |
        | .git                     [ ]       [ ]         [U]      |
        | A File Icon              [ ]       [I]         [ ]      |
        | ASP                      [S]       [ ]         [ ]      |
        | ActionScript             [S]       [ ]         [ ]      |
        +---------------------------------------------------------+
        with_col_seps = True:
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
        row_sep = self._single_line_row_separator(with_col_seps)

        lines.append(row_sep)

        if with_col_seps:
            col_prefix            = ' '
            col_suffix            = ' |'
            last_col_suffix       = ' |'
            tight_col_suffix      = '|'
            tight_last_col_suffix = '|'
        else:
            col_prefix            = ' '
            col_suffix            = '  '
            last_col_suffix       = ' |'
            tight_col_suffix      = ' '
            tight_last_col_suffix = '|'

        for row in self.table:
            line_parts.clear()

            if indent:
                line_parts.append(indent)

            line_parts.append('|')
            last_i = len(row) - 1

            for i, col in enumerate(row):
                col_repr = f'{col:{self.column_alignments[i]}{self.max_column_widths[i]}}'
                if self.tight_columns[i]:
                    line_parts.append(col_repr)
                    if i == last_i:
                        line_parts.append(tight_last_col_suffix)
                    else:
                        line_parts.append(tight_col_suffix)
                else:
                    line_parts.append(col_prefix)
                    line_parts.append(col_repr)
                    if i == last_i:
                        line_parts.append(last_col_suffix)
                    else:
                        line_parts.append(col_suffix)

            line = ''.join(line_parts)
            lines.append(line)

        lines.append(row_sep)

        return '\n'.join(lines)

    def _restructuredtext_repr(self, indent: str):
        """
        +------------------------+---------+-----------+----------+
        | Package                | Shipped | Installed | Unpacked |
        +========================+=========+===========+==========+
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
        row_sep = indent + self._single_line_row_separator(True)
        title_sep = indent + self._double_line_row_separator(True)

        lines.append(row_sep)

        for ri, row in enumerate(self.table):
            line_parts.clear()

            if indent:
                line_parts.append(indent)

            line_parts.append('|')

            for ci, col in enumerate(row):
                col_repr = f'{col:{self.column_alignments[ci]}{self.max_column_widths[ci]}}'
                if self.tight_columns[ci]:
                    line_parts.append(col_repr)
                    line_parts.append('|')
                else:
                    line_parts.append(' ')
                    line_parts.append(col_repr)
                    line_parts.append(' |')

            line = ''.join(line_parts)
            lines.append(line)

            if ri == 0:
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
    # ``rows`` is now a list[list[str]] needed by ``AsciiTable``.
    # ---------------------------------------------------------------------
    table = AsciiTable(rows)
    # table.set_column_alignments(['', '^', '^', '^'])
    print(repr(table))
    print(table.to_string(Format.BARE))
    print(table.to_string(Format.OUTLINED))
    print(table.to_string(Format.RESTRUCTUREDTEXT))
