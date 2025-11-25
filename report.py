# report.py

r'''Reports, both pdf and text, in rows and columns

Steps:

    1. Create Report object:

        report = Report("T-Report",  # this will be the filename

                        title=(Centered(span=2, size="title", bold=True),),
                        l0=(Left(bold=True), Right()),
                        l1=(Left(indent=1, bold=True), Right(indent=1)),
                        l2=(Left(indent=2, bold=True), Right(indent=2)),
                        l3=(Left(indent=3), Right(indent=3)),
                       )

    2. Create a row.  These will be output in the order created:

        title_row = report.new_row("title")
    
    3. Add text to columns.  This may be done after other rows are created.

        title_row.next_cell("Treasurer's Report")  # can override size and/or bold here

        # optional:
        title_row.set_text2("...")                 # Tack text onto the end of the last cell.
                                                   # Can specify bold (default False).

    4. initialize the report.  These print the size of the report to stdout:

        report.draw_init()
     or report.print_init()

    5. generate the report:

        report.draw()   # may send x_offset and/or y_offset (from top) to transpose report on page
                        # file generated in ~/storage/downloads/<report-name>.pdf
     or report.print()  # may send file argument, otherwise report is sent to stdout.

'''

# letter page size is 612 x 792

# y values:
#   top of "l"                         =  71.8%
#   top of "g"                         =  54%
#   bottom of "l"                      =   0%
#   bottom of "g" (excluding decender) =  -1%
#   bottom of "g" decender             = -22%
#
# x values:
#   left of "g"                        =   4%
#   right of "g"                       =  50.02%
#   width of "g"                       =  46.02%
#   right of "l"                       =  74.8%
#   right of stringWidth("gl")         =  83.4%
#   stringWidth("g")           360.288 =  55.6%
#   stringWidth("l")           143.856 =  22.2%
#   stringWidth(" ")           180.144 =  27.8%

from pathlib import Path
import sys

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, portrait, letter, inch


class Report:
    default_font = 'Helvetica'
    default_bold = 'Helvetica-Bold'
    default_size = 13
    title_size   = 17

    indent_chars  = 4
    indent_points = indent_chars * default_size * 0.278

    col_gap_chars = 3
    col_gap_points = col_gap_chars * default_size * 0.278

    def __init__(self, name, path=Path("~/storage/downloads/"), **row_layout_cols):
        self.name = name
        path = (Path("~/storage/downloads") / (name + ".pdf")).expanduser()
        print(f"Report({name=}): {path=}")
        self.canvas = canvas.Canvas(str(path), pagesize=portrait(letter))
        self.page_width, self.page_height = portrait(letter)

        # Column_layouts
        self.columns = {}
        self.name_suffixes = {}   # {col_name: next_suffix}
        self.col_x_starts = [0] * (len(row_layout_cols) + 1)
        self.col_x_char_starts = [0] * (len(row_layout_cols) + 1)

        # Row_layouts
        self.row_layouts = {}     # {row_name: row_layout}
        for rl_name, cols in row_layout_cols.items():
            for col_index, col in enumerate(cols):
                col.set_report(self, col_index)
            self.row_layouts[rl_name] = Row_layout(self, rl_name, *cols)

        # Rows
        self.rows = []

    def new_row(self, row_layout):
        return self.row_layouts[row_layout].new_row()

    def init(self):
        self.set_sizes()
        self.set_y_starts()
        self.set_x_starts()

    def draw_init(self):
        self.init()
        print("Report width", self.report_width(), "height", self.report_height())

    def draw(self, x_offset=0, y_offset=0):
        for row in self.rows:
            if row.print:
                for cell in row.cells:
                    cell.draw(x_offset, y_offset)

    def print_init(self):
        self.init()
        print("Report width", self.report_width_chars(), "height", self.report_height_chars())

    def print(self, file=sys.stdout):
        for row in self.rows:
            if row.print:
                for cell in row.cells:
                    cell.print(file)
                print(file=file)

    def make_col_name(self, col_name):
        if col_name not in self.name_suffixes:
            self.name_suffixes[col_name] = 1
        ans = f"{col_name}-{self.name_suffixes[col_name]}"
        self.name_suffixes[col_name] += 1
        return ans

    def register_column(self, col_layout):
        assert col_layout.name not in self.columns, f"Duplicate Column name={col_layout.name}"
        self.columns[col_layout.name] = col_layout

    def add_row(self, row):
        self.rows.append(row)
        return len(self.rows)

    def set_sizes(self):
        for row in self.rows:
            if row.print:
                for cell in row.cells:
                    cell.set_sizes()

    def set_y_starts(self):
        BM(self)  # add dummy bottom margin row to capture the height of the report.
        for i, row in enumerate(self.rows[:-1]):
            self.rows[i + 1].set_y_start(row.y_start + row.height, row.y_char_start + row.height_chars)

    def set_x_starts(self):
        for i in range(len(self.col_x_starts)):  # all col_x_starts have been taken care of up to and including i
            for col in self.columns.values():
                if col.left_index == i:
                    right_start = self.col_x_starts[col.left_index] + col.my_width + self.col_gap_points
                    if right_start > self.col_x_starts[col.right_index]:
                        self.col_x_starts[col.right_index] = right_start
                    right_char_start = \
                      self.col_x_char_starts[col.left_index] + col.my_width_chars + self.col_gap_chars
                    if right_char_start > self.col_x_char_starts[col.right_index]:
                        self.col_x_char_starts[col.right_index] = right_char_start

    def report_height(self):
        return self.rows[-1].y_start

    def report_height_chars(self):
        return self.rows[-1].y_char_start

    def report_width(self):
        return self.col_x_starts[-1]

    def report_width_chars(self):
        return self.col_x_char_starts[-1]


class Cell:
    def __init__(self, text, col, row, size=None, bold=None):
        self.text = text or ''
        self.col = col
        self.row = row
        self.size = size if size is not None else self.col.fontsize
        self.bold = bold if bold is not None else self.col.bold
        if self.bold:
            self.fontName = self.col.report.default_bold
        else:
            self.fontName = self.col.report.default_font
        self.width1 = self.col.report.canvas.stringWidth(str(self.text), fontName=self.fontName,
                                                         fontSize=self.size)
        self.text2 = None
        self.bold2 = None
        self.width2 = 0

    def set_text2(self, text2, bold=False):
        assert self.text2 is None, \
               f"Second call to Cell.set_text2, first text2={self.text2}, this {text2=}"
        self.text2 = text2
        self.bold2 = bold
        if self.bold2:
            self.fontName2 = self.col.report.default_bold
        else:
            self.fontName2 = self.col.report.default_font
        self.width1 += self.col.report.gap_width
        self.width2 = self.col.report.canvas.stringWidth(str(self.text2), fontName=self.fontName2,
                                                         fontSize=self.size)

    def set_sizes(self):
        self.col.set_width(self.my_width(), self.my_width_chars())
        self.row.set_height(self.my_height(), 1)

    def my_height(self):
        r'''In points.
        '''
        return self.size

    def my_width(self):
        r'''In points.
        '''
        return self.width1 + self.width2

    def my_width_chars(self):
        r'''In characters.
        '''
        width1 = len(str(self.text))
        if self.text2 is None:
            width2 = 0
        else:
            width2 = len(str(self.text2))
            width2 += self.col.report.gap_width_chars
        return width1 + width2

    def draw(self, x_offset, y_offset):
        self.col.report.canvas.setFont(self.fontName, self.size)
        x = self.col.get_x_offset(self.my_width())
        self.col.report.canvas.drawString(x + x_offset,
                                          self.col.report.page_height - (y_offset + self.row.y_end),
                                          str(self.text))

        if self.text2 is not None:
            self.col.report.canvas.setFont(self.fontName2, self.size)
            self.col.report.canvas.drawString(x + x_offset + self.width1,
                                              self.col.report.page_height - (y_offset + self.row.y_end),
                                              str(self.text))

    def print(self, file):
        text = self.text
        if self.text2 is not None:
            text += ' ' * self.col.report.gap_width_chars
            text += self.text2
        left, right = self.col.get_padding(len(text))
        print(' ' * left, text, ' ' * right, sep='', end='')


# Column layouts:

class Column_layout:
    report = None

    def __init__(self, name=None, span=1, indent_level=0, size=None, bold=False):
        self.name = name
        self.span = span
        self.indent_level = indent_level
        self.fontsize = size
        self.bold = bold

    def set_report(self, report, col_index):
        self.report = report
        self.left_index = col_index
        self.right_index = self.left_index + self.span
        if self.name is None:
            self.name = report.make_col_name(self.__class__.__name__)
        report.register_column(self)
        self.indent = self.indent_level * report.indent_points
        self.indent_chars = self.indent_level * report.indent_chars
        if self.fontsize is None:
            self.fontsize = report.default_size
        elif isinstance(self.fontsize, str):
            self.fontsize = getattr(report, self.fontsize + "_size")
        self.my_width = 0
        self.my_width_chars = 0

    def set_width(self, points, chars):
        if points > self.my_width:
            self.my_width = points
        if chars > self.my_width_chars:
            self.my_width_chars = chars

    @property
    def x_start(self):
        return self.report.col_x_starts[self.left_index]

    @property
    def x_char_start(self):
        return self.report.col_x_char_starts[self.left_index]

    def width(self):
        return self.report.col_x_starts[self.right_index] - self.x_start

    def width_chars(self):
        return self.report.col_x_char_starts[self.right_index] - self.x_char_start

class Left(Column_layout):
    def get_x_offset(self, text_width):
        return self.x_start + self.indent

    def get_padding(self, text_width):
        r'''Returns num spaces to print to the left and right of text.
        '''
        return self.indent_chars, self.width_chars() - self.indent_chars - text_width

class Centered(Column_layout):
    r'''No indent on these...
    '''
    def get_x_offset(self, text_width):
        ans = self.x_start + self.width() / 2 - text_width / 2
        print(f"Centered({self.name}).get_x_offset({text_width=}): {self.x_start=}, {self.width()=} -> {ans}")
        return ans

    def get_padding(self, text_width):
        r'''Returns num spaces to print to the left and right of text.
        '''
        left = (self.width_chars() - text_width) // 2
        right = self.width_chars() - text_width - left
        return left, right

class Right(Column_layout):
    r'''Assumes text is a Decimal with 2 digits after the decimal point, so just aligns right rather than
    aligning on decimal point.
    '''
    def get_x_offset(self, text_width):
        return self.x_start + self.col.width() - self.indent - text_width

    def get_padding(self, text_width):
        r'''Returns num spaces to print to the left and right of text.
        '''
        right = self.indent_chars
        left = self.width_chars() - self.indent_chars - text_width
        return left, right


class Row_layout:
    def __init__(self, report, name, *columns):
        r'''columns are either a Column_layout instance, or name.
        '''
        self.report = report
        self.name = name
        self.columns = columns

    def new_row(self):
        return Row(self)


class BM:
    r'''Bottom Margin.
    '''
    print = False

    def __init__(self, report):
        self.y_start = 0
        self.y_char_start = 0
        self.row_num = report.add_row(self)  # NOTE: 1 greater than index into report.rows

    def set_y_start(self, y, y_char):
        if y > self.y_start:
            self.y_start = y
        if y_char > self.y_char_start:
            self.y_char_start = y_char

class Row(BM):
    print = True

    def __init__(self, layout):
        super().__init__(layout.report)
        self.layout = layout
        self.column_index = 0
        self.height = 0
        self.height_chars = 0
        self.cells = []

    def set_height(self, points, chars):
        if points > self.height:
            self.height = points
        if chars > self.height_chars:
            self.height_chars = chars

    @property
    def y_end(self):
        return self.y_start + self.height

    def next_cell(self, text=None, size=None, bold=None):
        r'''Doesn't return anything.
        '''
        assert self.column_index < len(self.layout.columns), f"Row({self.row_num}).next_cell: too many calls"
        cell = Cell(text, self.layout.columns[self.column_index], self, size=size, bold=bold)
        self.cells.append(cell)
        self.column_index += 1

    def set_text2(self, text, bold=False):
        r'''Adds text to the end of the last cell.
        '''
        self.cells[-1].set_text2(text, bold)


def dump_table():
    import argparse
    import database

    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", "-p", action="store_true", default=False)
    parser.add_argument("table")

    args = parser.parse_args()

    database.load_database()

    table_name = args.table
    table = getattr(database, table_name)

    header_cols = []
    data_cols = []
    header_names = []
    for name, type in table.row_class.types.items():
        header_names.append(name)
        if type in (int, float, database.Decimal):
            header_cols.append(Right(bold=True))
            data_cols.append(Right())
        else:
            header_cols.append(Left(bold=True))
            data_cols.append(Left())

    report = Report(table_name,
           title=(Centered(span=len(header_names), size='title', bold=True),),
           headers=header_cols,
           data=data_cols,
          )
    report.new_row('title').next_cell(table_name)
    headers = report.new_row('headers')
    for name in header_names:
        headers.next_cell(name)
    for row in table.values():
        data = report.new_row('data')
        for name in header_names:
            value = getattr(row, name)
            if value is None:
                data.next_cell()
            else:
                data.next_cell(value)

    if args.pdf:
        report.draw_init()
        report.draw()
        report.canvas.showPage()
        report.canvas.save()
    else:
        report.print_init()
        report.print()



if __name__ == "__main__":
    dump_table()
