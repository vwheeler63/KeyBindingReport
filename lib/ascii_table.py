from typing import List, Iterable
from enum import IntEnum


class Format(IntEnum):
    """
    Formats supported by Generator
    """
    BARE = 0
    OUTLINED = 1
    RESTRUCTUREDTEXT = 2


class Generator():
    """
    ASCII Tables that can generate representations of themselves
    in a variety of formats.
    """
    __slots__ = ['data', 'row_count', 'column_count', 'max_column_widths']

    def __init__(self, data: List[Iterable[str]]):
        self.data = data
        self._gather_metadata()

    def __repr__(self):
        result = f'{{Generator: rows={self.row_count}, cols={self.column_count}}}\n'
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
        Default                [S]   [ ]   [U]
        .git                   [ ]   [ ]   [U]
        A File Icon            [ ]   [I]   [ ]
        ASP                    [S]   [ ]   [ ]
        ActionScript           [S]   [ ]   [ ]
        AppleScript            [S]   [ ]   [ ]

        Default column separation == 3 spaces.
        """
        lines = []
        line_parts = []
        col_sep = '   '

        # Build table in `lines` list.
        for row in self.data:
            line_parts.clear()
            last_col_idx = len(row) - 1
            for col in row:
                line_parts.append(col)
            line = col_sep.join(line_parts)
            lines.append(line)

        return '\n'.join(lines)


    def _outlined_string_repr(self):
        """
        +------------------------+-----+-----+-----+
        | Default                | [S] | [ ] | [U] |
        | .git                   | [ ] | [ ] | [U] |
        | A File Icon            | [ ] | [I] | [ ] |
        | ASP                    | [S] | [ ] | [ ] |
        | ActionScript           | [S] | [ ] | [ ] |
        | AppleScript            | [S] | [ ] | [ ] |
        +------------------------+-----+-----+-----+
        """
        lines = []
        line_parts = []
        row_sep = self._single_line_row_separator()

        # Build table in `lines` list.
        lines.append(row_sep)

        for row in self.data:
            line_parts.clear()
            line_parts.append('|')
            for col in row:
                line_parts.append(' ')
                line_parts.append(col)
                line_parts.append(' |')
            line = ''.join(line_parts)
            lines.append(line)

        lines.append(row_sep)

        return '\n'.join(lines)


    def _restructuredtext_string_repr(self):
        """
        +------------------------+-----+-----+-----+
        | Default                | [S] | [ ] | [U] |
        +========================+=====+=====+=====+
        | .git                   | [ ] | [ ] | [U] |
        +------------------------+-----+-----+-----+
        | A File Icon            | [ ] | [I] | [ ] |
        +------------------------+-----+-----+-----+
        | ASP                    | [S] | [ ] | [ ] |
        +------------------------+-----+-----+-----+
        | ActionScript           | [S] | [ ] | [ ] |
        +------------------------+-----+-----+-----+
        | AppleScript            | [S] | [ ] | [ ] |
        +------------------------+-----+-----+-----+
        """
        lines = []
        line_parts = []
        row_sep = self._single_line_row_separator()
        title_sep = self._double_line_row_separator()

        # Build table in `lines` list.
        lines.append(row_sep)
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
            else:
                lines.append(row_sep)

        return '\n'.join(lines)


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
    # ``rows`` is now a List[Iterable[str]] needed by ``Generator``.
    # ---------------------------------------------------------------------
    at = Generator(rows)
    print(repr(at))
    print(at.as_string(Format.BARE))
    print(at.as_string(Format.OUTLINED))
    print(at.as_string(Format.RESTRUCTUREDTEXT))
