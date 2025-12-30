# table.py

import os
import os.path
import csv
from statistics import mean

from row import *


Database_filename = "beans.csv"

CSV_dialect = 'excel'  # 'excel', 'excel-tab' or 'unix'
CSV_format = dict(delimiter='|', quoting=csv.QUOTE_NONE, skipinitialspace=True, strict=True)


def align(value, width, alignment):
    if alignment == 'right':
        return ' ' * (width - len(value)) + value
    return value + ' ' * (width - len(value))

class base_table:
    def __init__(self, row_class):
        self.row_class = row_class

    @property
    def name(self):
        return self.row_class.__name__

    def check_foreign_keys(self):
        r'''Returns the number of errors found.
        '''
        errors = 0
        for row_num, row in enumerate(self.values(), 1):
            if not row.check_foreign_keys(row_num, False):
                errors += 1
        return errors

    def insert(self, **attrs):
        self.add_row(self.row_class(**attrs))

    def insert_from_csv(self, header, row, ignore_unknown_cols=False, skip_fk_check=False):
        self.add_row(self.row_class.from_csv(header, row, ignore_unknown_cols=ignore_unknown_cols),
                     skip_fk_check=skip_fk_check)

    def from_csv(self, csv_reader, from_scratch=True, ignore_unknown_cols=False, skip_fk_check=False):
        r'''Loads rows from csv_reader.  First row is header row that identifies the attrs.

        If from_scratch is False, appends the rows to the current contents; otherwise it replaces
        the current contents.
        '''
        if from_scratch:
            self.clear()
        header = next(csv_reader)
        try:
            while True:
                row = next(csv_reader)
                if len(row) == 0:
                    break
                self.insert_from_csv(header, row, ignore_unknown_cols=ignore_unknown_cols,
                                     skip_fk_check=skip_fk_check)
        except StopIteration:
            pass

    def to_csv(self, file, add_table_name=True, add_empty_row=False):
        r'''Writes itself in database csv format to file.
        '''
        if add_table_name:
            print(self.name, file=file)                 # first line is name of table (only one column)
        widths = {}
        alignments = {}
        headers = tuple(self.row_class.types.keys())
        header_row = []
        for name in headers:
            name = name.lower()
            max_width = len(name)
            if self.row_class.types[name] in (int, float, Decimal):
                alignment = 'right'
            else:
                alignment = 'left'
            alignments[name] = alignment
            for row in self.values():
                if getattr(row, name) is not None:
                    width = len(row.csv_value(name))
                    if width > max_width:
                        max_width = width
            widths[name] = max_width
            header_row.append(align(name, max_width, alignment))
        print('|'.join(header_row), file=file)
        for row in self.values():
            values = []
            for name in headers:
                value = row.csv_value(name)
                if value is None:
                    values.append(' ' * widths[name])
                else:
                    values.append(align(value, widths[name], alignments[name]))
            print('|'.join(values), file=file)          # data line.
        if add_empty_row:
            print(file=file)                            # empty row terminator

    def dump(self):
        r'''Dumps the table to stdout, one line per row.
        '''
        print(f"{self.name}:")
        for row in self.values():
            print('   ', end='')
            row.dump()

class table_unique(base_table, dict):
    def __init__(self, row_class):
        base_table.__init__(self, row_class)
        dict.__init__(self)

    def add_row(self, row, skip_fk_check=False):
        key = row.key()
        if not skip_fk_check:
            row.check_foreign_keys(key, raise_exc=True)
        assert key not in self, f"{self.name}.insert: Duplicate {key=}"
        self[key] = row

class Months(table_unique):
    @staticmethod
    def inc_month(year, month):
        r'''Returns next month (regardless of the contents of this Table) as (year, month).

        Does not skip over May-Oct.
        '''
        if month == 12:
            return year + 1, 1
        return year, month + 1

    @staticmethod
    def dec_month(year, month):
        r'''Returns prior month (regardless of the contents of this Table) as (year, month).

        Does not skip over May-Oct.
        '''
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def last_month(self):
        r'''Returns the last month in the table.
        '''
        today = date.today()
        year = today.year
        month = today.month
        if (year, month) in self:
            year2, month2 = self.inc_month(year, month)
            while (year2, month2) in self:
                year, month = year2, month2
                year2, month2 = self.inc_month(year, month)
            return self[year, month]
        year, month = self.dec_month(year, month)
        while (year, month) not in self:
            year, month = self.dec_month(year, month)
        return self[year, month]

    def by_month(self, month):
        r'''Generates all rows with this month.
        '''
        for row in self.values():
            if row.month == month:
                yield row

    def avg(self, month, attr):
        rows = [row for row in self.by_month(month) if getattr(row, attr) is not None]
        if not rows:
            return None
        return round(mean(getattr(row, attr) for row in rows))

    def avg_num_at_meeting(self, month):
        return self.avg(month, 'num_at_meeting')

    def avg_staff_at_breakfast(self, month):
        return self.avg(month, 'staff_at_breakfast')

    def avg_tickets_claimed(self, month):
        return self.avg(month, 'tickets_claimed')

    def avg_meals_served(self, month):
        return self.avg(month, 'meals_served')

class table_by_date(base_table, list):
    def __init__(self, row_class):
        base_table.__init__(self, row_class)
        list.__init__(self)

    def first_date(self, date):
        r'''Returns index to the first date == `date`.
        '''
        return self.find_date(date, find_first=True)

    def last_date(self, date):
        r'''Returns index to smallest date > `date`.
        '''
        return self.find_date(date, find_first=False)

    def find_date(self, date, find_first):
        r'''This returns the index at which to insert `date`.

        The find_first parameter disambiguates the case where one or more matching dates already
        appear in the file.

        If find_first is True, `date` will be inserted _before_ all other matching dates.  This means that
        the index returned is to the first matching date.

        If find_first is False, `date` will be inserted _after_ all other matching dates.  This means that
        the index returned is just after the last matching date.  It also means that the index returned
        may equal length of the file, meaning that it does not point to any row in the file.
        '''
        first = 0              # ignore < first
        last = len(self)       # ignore >= last
        while first < last:
            i = (last + first) // 2  # might be first, but never last
            if date < self[i].date:
                last = i
            elif date > self[i].date:
                first = i + 1
            elif find_first:
                last = i
            else:
                first = i + 1
        # first == last
        return first

    def add_row(self, row, skip_fk_check=False):
        if hasattr(row, 'date'):
            i = self.last_date(row.date)
           #print(f"{self.name}.add_row(date={row.date}), inserted at {i=}")
            list.insert(self, i, row)
            if not skip_fk_check:
                row.check_foreign_keys(row.date, raise_exc=True)
        else:
            if not skip_fk_check:
                row.check_foreign_keys(len(self) + 1, raise_exc=True)
            self.append(row)
    
    def values(self):
        return self

def table_for_row(row_class):
    if row_class.table_name == "Months":
        return Months(row_class)
    if row_class.primary_key is not None or row_class.primary_keys is not None:
        return table_unique(row_class)
    return table_by_date(row_class)

Tables = {row_class.table_name: table_for_row(row_class) for row_class in Rows}

class DB:
    def __init__(self, tables):
        for name, table in tables.items():
            setattr(self, name, table)

Database = DB(Tables)

set_database(Database)


__all__ = "CheckInventory Decimal date datetime timedelta bills abbr_month Tables Database " \
          "load_database save_database load_csv load_all clear_all check_foreign_keys " \
          "CSV_dialect CSV_format".split()


def load_database(csv_filename=Database_filename, ignore_unknown_cols=False):
    r'''Loads the database tables.
    '''
    with open(csv_filename, 'r') as f:
        reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        ans = {}
        while True:
            try:
                header = next(reader)
                assert len(header) == 1, f"from_csv: Expected table name, got {row=}"
                ans[header[0].strip()] = \
                  Tables[header[0].strip()].from_csv(reader, ignore_unknown_cols=ignore_unknown_cols,
                                                     skip_fk_check=True)
            except StopIteration:
                break
    return ans

def save_database(csv_filename=Database_filename):
    temp_filename = csv_filename[:-4] + '-new.csv'
    with open(temp_filename, 'w') as f:
        for table in Tables.values():
            if table.row_class.in_database:
                table.to_csv(f, add_empty_row=True)
    save_filename = csv_filename[:-4] + '-save.csv'
    os.replace(csv_filename, save_filename)
    os.rename(temp_filename, csv_filename)

def load_csv(csv_filename, from_scratch=True, ignore_unknown_cols=False):
    r'''Loads table from csv_filename.

    clears current contents of table if from_scratch is True, otherwise, rows are appended.

    If csv_filename has no .csv suffix, one is added.
    '''
    if not csv_filename.endswith(".csv"):
        csv_filename += ".csv"
    with open(csv_filename, 'r') as f:
        csv_reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        row1 = next(csv_reader)
        assert len(row1) == 1, f"load_csv: Expected table name, got {row1=}"
        table_name = row1[0].strip()
        Tables[table_name].from_csv(csv_reader, from_scratch=from_scratch, ignore_unknown_cols=ignore_unknown_cols)

def load_all(from_scratch=True, ignore_unknown_cols=False):
    for table in Tables.values():
        if os.path.exists(f"{table.name}.csv"):
            print("loading:", table.name)
            load_csv(table.name, from_scratch=from_scratch, ignore_unknown_cols=ignore_unknown_cols)
        else:
            print("load_all: skipping", table.name)

def clear_all():
    for table in reversed(Tables.values()):
        table.clear()

def check_foreign_keys():
    errors = 0
    for table in Tables.values():
        errors += table.check_foreign_keys()
    if errors:
        print("Total errors:", errors)
    else:
        print("No errors found")

def run():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", "-i", action="store_true", default=False, help="init database to all empty tables")
    parser.add_argument("--ignore-unknown-cols", "-u", action="store_true", default=False)
    parser.add_argument("--load", "-l", default=None, help="load one separate csv table")
    parser.add_argument("--save", "-s", default=None, help="save one separate csv table")
    parser.add_argument("--load-all", "-a", action="store_true", default=False, help="load all separate csv tables")
    parser.add_argument("--no-save", "-n", action="store_true", default=False, help="skip final database save")
    parser.add_argument("--check-foreign-keys", "-c", action="store_true", default=False)

    args = parser.parse_args()

    if args.init:
        # create empty database csv file.
        clear_all()
    else:
        load_database(ignore_unknown_cols=args.ignore_unknown_cols)
    if args.load_all:
        load_all(from_scratch=True, ignore_unknown_cols=args.ignore_unknown_cols)
    elif args.load is not None:
        print("loading:", args.load + '.csv')
        load_csv(args.load, ignore_unknown_cols=args.ignore_unknown_cols)
    if args.check_foreign_keys:
        check_foreign_keys()
    if args.save is not None:
        with open(f"{args.save}.csv", "w") as f:
            print("saving:", args.save + '.csv')
            Tables[args.save].to_csv(f)

    if not args.no_save:
        save_database()



if __name__ == "__main__":
   #for name, t in Tables.items():
   #    print(name, t)
    run()

