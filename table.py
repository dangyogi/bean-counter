# table.py

import os.path
import csv

from row import *


Database_filename = "beans.csv"

CSV_dialect = 'excel'  # 'excel', 'excel-tab' or 'unix'
CSV_format = dict(delimiter='|', quoting=csv.QUOTE_NONE, skipinitialspace=True, strict=True)


class base_table:
    def __init__(self, row_class):
        self.row_class = row_class

    @property
    def name(self):
        return self.row_class.__name__

    def insert(self, **attrs):
        self.add_row(self.row_class(**attrs))

    def load_csv(self, csv_filename=None, from_scratch=True, ignore_unknown_cols=False):
        r'''Loads table from csv_filename.

        clears current contents of table if from_scratch is True, otherwise, rows are appended.

        csv_filename defaults to f"{self.name}.csv".
        '''
        if csv_filename is None:
            csv_filename = f"{self.name}.csv"
        with open(csv_filename, 'r') as f:
            self.from_csv(csv.reader(f, CSV_dialect, **CSV_format),
                          from_scratch=from_scratch,
                          ignore_unknown_cols=ignore_unknown_cols)

    def from_csv(self, csv_reader, from_scratch=True, ignore_unknown_cols=False):
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
                self.add_row(self.row_class.from_csv(header, row, ignore_unknown_cols=ignore_unknown_cols))
        except StopIteration:
            pass

    def to_csv(self, file, add_empty_row=False):
        r'''Writes itself in database csv format to file.
        '''
        print(self.name, file=file)                     # first line is name of table (only one column)
        print(self.row_class.csv_header(), file=file)   # header line with attr names.
        for row in self.values():
            print(row.to_csv(), file=file)              # data line.
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

    def add_row(self, row):
        key = row.key()
        assert key not in self, f"{self.name}.insert: Duplicate {key=}"
        self[key] = row

class table_by_date(base_table, list):
    def __init__(self, row_class):
        base_table.__init__(self, row_class)
        list.__init__(self)

    def first_date(self, date):
        return self.find_date(date, find_first=True)

    def last_date(self, date):
        r'''Returns index to smallest date > `date`.
        '''
        return self.find_date(date, find_first=False)

    def find_date(self, date, find_first):
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

    def add_row(self, row):
        i = self.last_date(row.date)
       #print(f"{self.name}.add_row(date={row.date}), inserted at {i=}")
        list.insert(self, i, row)
    
    def values(self):
        return self


Tables = {row_class.table_name: (table_by_date(row_class) if row_class.primary_key is None and row_class.primary_keys is None
                                                          else table_unique(row_class))
          for row_class in Rows}


__all__ = "Decimal date Tables load_database save_database load_all clear_all".split()


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
                  Tables[header[0].strip()].from_csv(reader, ignore_unknown_cols=ignore_unknown_cols)
            except StopIteration:
                break
    return ans

def save_database(csv_filename=Database_filename):
    with open(csv_filename, 'w') as f:
        for table in Tables.values():
            table.to_csv(f, add_empty_row=True)

def load_all(from_scratch=True, ignore_unknown_cols=False):
    for table in Tables.values():
        if os.path.exists(f"{table.name}.csv"):
            print("loading:", table.name)
            table.load_csv(from_scratch=from_scratch, ignore_unknown_cols=ignore_unknown_cols)
        else:
            print("load_all: skipping", table.name)

def clear_all():
    for table in reversed(Tables.values()):
        table.clear()


def run():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", "-i", action="store_true", default=False)
    parser.add_argument("--ignore-unknown-cols", "-u", action="store_true", default=False)
    parser.add_argument("--load", "-l", default=None)
    parser.add_argument("--save", "-s", default=None)
    parser.add_argument("--load-all", "-a", action="store_true", default=False)

    args = parser.parse_args()


    if args.init:
        # create empty database csv file.
        clear_all()
    else:
        load_database(ignore_unknown_cols=args.ignore_unknown_cols)
    if args.load_all:
        load_all(from_scratch=True, ignore_unknown_cols=args.ignore_unknown_cols)
    elif args.load is not None:
        Tables[args.load].load_csv(from_scratch=True, ignore_unknown_cols=args.ignore_unknown_cols)
    if args.save is not None:
        with open(f"{args.save}.csv", "w") as f:
            Tables[args.save].to_csv(f)

    save_database()



if __name__ == "__main__":
   #for name, t in Tables.items():
   #    print(name, t)
    run()

