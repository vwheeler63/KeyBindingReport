from typing import List, Iterable
from enum import IntEnum


class AsciiTableFormat(IntEnum):
    """
    Formats supported by AsciiTable
    """
    OUTLINED = 0
    RESTRUCTUREDTEXT = 1


class AsciiTable():
    """
    ASCII Tables that can generate representations of themselves
    in a variety of formats.
    """
    __slots__ = ['data', 'row_count', 'column_count', 'max_column_widths']

    def __init__(self, data: List[Iterable[str]]):
        self.data = data
        self._gather_metadata()

    def __repr__(self):
        result = f'{{AsciiTable: rows={self.row_count}, cols={self.column_count}}}\n'
        for i, w in enumerate(self.max_column_widths):
            result += f'  Col {i + 1} max width: {w:>2}\n'
        return result

    def _gather_metadata(self):
        """ Gather information needed about `self.data` """
        self.row_count = len(self.data)
        self.column_count = 0
        self.max_column_widths = []

        for row in self.data:
            # Keep max in ``column_count`` and extend ``max_column_widths`` if needed.
            if (col_count := len(row)) > self.column_count:
                self.column_count = col_count
                while (curr_cols := len(self.max_column_widths)) < col_count:
                    self.max_column_widths.append(0)

            for i, field in enumerate(row):
                if (width := len(field)) > self.max_column_widths[i]:
                    self.max_column_widths[i] = width

    def as_string(self, fmt: AsciiTableFormat):
        """ Representation of `self` as a string """
        lines = []

        # -----------------------------------------------------------------
        # Prepare.
        # -----------------------------------------------------------------
        row_sep_parts = ['+']

        for max_w in self.max_column_widths:
            col_segment = '-' * (max_w + 2)
            row_sep_parts.append(col_segment)
            row_sep_parts.append('+')

        row_sep = ''.join(row_sep_parts)
        title_sep = ''

        if fmt == AsciiTableFormat.RESTRUCTUREDTEXT:
            row_sep_parts.clear()
            row_sep_parts.append('+')

            for max_w in self.max_column_widths:
                col_segment = '=' * (max_w + 2)
                row_sep_parts.append(col_segment)
                row_sep_parts.append('+')

            title_sep = ''.join(row_sep_parts)

        # -----------------------------------------------------------------
        # Build table.
        # -----------------------------------------------------------------
        lines.append(row_sep)
        line_parts = []

        if fmt == AsciiTableFormat.OUTLINED:
            for i, row in enumerate(self.data):
                line_parts.clear()
                line_parts.append('|')
                for col in row:
                    line_parts.append(' ')
                    line_parts.append(col)
                    line_parts.append(' |')
                line = ''.join(line_parts)
                lines.append(line)
        elif fmt == AsciiTableFormat.RESTRUCTUREDTEXT:
            last_row_idx = self.row_count - 1

            for i, row in enumerate(self.data):
                line_parts.clear()
                line_parts.append('|')
                for col in row:
                    line_parts.append(' ')
                    line_parts.append(col)
                    line_parts.append(' |')
                line = ''.join(line_parts)
                lines.append(line)

                if i == 0:
                    lines.append(title_sep)
                elif i < last_row_idx:
                    lines.append(row_sep)

        # After last line.
        lines.append(row_sep)

        # -----------------------------------------------------------------
        # Return string representation to caller.
        # -----------------------------------------------------------------
        return '\n'.join(lines)


if __name__ == '__main__':
    # ---------------------------------------------------------------------
    # Test
    # ---------------------------------------------------------------------
    with open('tab_sep_table_test.txt', 'r', encoding='utf-8') as f:
        # Default                \t[S]\t[ ]\t[U]
        content = f.read()
        lines = content.split('\n')
        rows = []

        for line in lines:
            fields = line.split('\t')
            rows.append(fields)

    # ---------------------------------------------------------------------
    # ``rows`` is now a List[Iterable[str]] needed by ``AsciiTable``.
    # ---------------------------------------------------------------------
    at = AsciiTable(rows)
    print(repr(at))
    print(at.as_string(AsciiTableFormat.OUTLINED))
    print(at.as_string(AsciiTableFormat.RESTRUCTUREDTEXT))
