# Copyright (c) 2015, Narrative Science
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
"""A module for pretty-printing tables."""
import os

def render_columns(columns, write_borders=True, column_colors=None):
    """
    Renders a list of columns.

    :param columns: A list of columns, where each column is a list of strings.
    :type columns: [[``str``]]
    :param write_borders: Whether to write the top and bottom borders.
    :type write_borders: ``bool``
    :param column_colors: A list of coloring functions, one for each column.
                          Optional.
    :type column_colors: [``str`` -> ``str``] or ``NoneType``

    :return: The rendered columns.
    :rtype: ``str``
    """
    if column_colors is not None and len(column_colors) != len(columns):
        raise ValueError('Wrong number of column colors')
    widths = [max(len(cell) for cell in column) for column in columns]
    max_column_length = max(len(column) for column in columns)
    result = '\n'.join(render_row(i, columns, widths, column_colors)
                       for i in range(max_column_length))
    if write_borders:
        border = '+%s+' % '|'.join('-' * (w + 2) for w in widths)
        return '%s\n%s\n%s' % (border, result, border)
    else:
        return result

def render_row(num, columns, widths, column_colors=None):
    """
    Render the `num`th row of each column in `columns`.

    :param num: Which row to render.
    :type num: ``int``
    :param columns: The list of columns.
    :type columns: [[``str``]]
    :param widths: The widths of each column.
    :type widths: [``int``]
    :param column_colors: An optional list of coloring functions.
    :type column_colors: [``str`` -> ``str``] or ``NoneType``

    :return: The rendered row.
    :rtype: ``str``
    """
    row_str = '|'
    cell_strs = []
    for i, column in enumerate(columns):
        try:
            cell = column[num]
            # We choose the number of spaces before we color the string, so
            # that the coloring codes don't affect the length.
            spaces = ' ' * (widths[i] - len(cell))
            if column_colors is not None and column_colors[i] is not None:
                cell = column_colors[i](cell)
            cell_strs.append(' %s%s ' % (cell, spaces))
        except IndexError:
            # If the index is out of range, just print an empty cell.
            cell_strs.append(' ' * (widths[i] + 2))
    return '|%s|' % '|'.join(cell_strs)

def render_table(table, write_borders=True, column_colors=None):
    """
    Renders a table. A table is a list of rows, each of which is a list
    of arbitrary objects. The `.str` method will be called on each element
    of the row. Jagged tables are ok; in this case, each row will be expanded
    to the maximum row length.

    :param table: A list of rows, as described above.
    :type table: [[``object``]]
    :param write_borders: Whether there should be a border on the top and
                          bottom. Defaults to ``True``.
    :type write_borders: ``bool``
    :param column_colors: An optional list of coloring *functions* to be
                          applied to each cell in each column. If provided,
                          the list's length must be equal to the maximum
                          number of columns. ``None`` can be mixed in to this
                          list so that a selection of columns can be colored.
    :type column_colors: [``str`` -> ``str``] or ``NoneType``

    :return: The rendered table.
    :rtype: ``str``
    """
    prepare_rows(table)
    columns = transpose_table(table)
    return render_columns(columns, write_borders, column_colors)

def transpose_table(table):
    """
    Transposes a table, turning rows into columns.
    :param table: A 2D string grid.
    :type table: [[``str``]]

    :return: The same table, with rows and columns flipped.
    :rtype: [[``str``]]
    """
    if len(table) == 0:
        return table
    else:
        num_columns = len(table[0])
        return [[row[i] for row in table] for i in range(num_columns)]

def prepare_rows(table):
    """
    Prepare the rows so they're all strings, and all the same length.

    :param table: A 2D grid of anything.
    :type table: [[``object``]]

    :return: A table of strings, where every row is the same length.
    :rtype: [[``str``]]
    """
    num_columns = max(len(row) for row in table)
    for row in table:
        while len(row) < num_columns:
            row.append('')
        for i in range(num_columns):
            row[i] = str(row[i]) if row[i] is not None else ''
    return table

def get_table_width(table):
    """
    Gets the width of the table that would be printed.
    :rtype: ``int``
    """
    columns = transpose_table(prepare_rows(table))
    widths = [max(len(cell) for cell in column) for column in columns]
    return len('+' + '|'.join('-' * (w + 2) for w in widths) + '+')
