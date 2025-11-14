# table.py

import os.path
import csv

from row import *


Database_filename = "beans.csv"

CSV_dialect = 'excel'  # 'excel', 'excel-tab' or 'unix'
CSV_format = dict(delimiter='|', quoting=csv.QUOTE_NONE, skipinitialspace=True, strict=True)


class table(dict):
    def __init__(self, row_class):
        super().__init__()
        self.row_class = row_class

    @property
    def name(self):
        return self.row_class.__name__

    def add_row(self, row):
        key = row.key()
        assert key not in self, f"{self.name}.insert: Duplicate {key=}"
        self[key] = row

    def insert(self, **attrs):
        self.add_row(self.row_class(**attrs))

    def load_csv(self, csv_filename=None, from_scratch=True):
        r'''Loads table from csv_filename.

        clears current contents of table if from_scratch is True, otherwise, rows are appended.

        csv_filename defaults to f"{self.name}.csv".
        '''
        if csv_filename is None:
            csv_filename = f"{self.name}.csv"
        with open(csv_filename, 'r') as f:
            self.from_csv(csv.reader(f, CSV_dialect, **CSV_format), from_scratch=from_scratch)

    def from_csv(self, csv_reader, from_scratch=True):
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
                self.add_row(self.row_class.from_csv(header, row))
        except StopIteration:
            pass

    def to_csv(self, file):
        r'''Writes itself in database csv format to file.
        '''
        print(self.name, file=file)                     # first line is name of table (only one column)
        print(self.row_class.csv_header(), file=file)   # header line with attr names.
        for row in self.values():
            print(row.to_csv(), file=file)              # data line.
        print(file=file)                                # empty row terminator

    def dump(self):
        r'''Dumps the table to stdout, one line per row.
        '''
        print(f"{self.name}:")
        for row in self.values():
            print('   ', end='')
            row.dump()

Tables = {row_class.table_name: table(row_class) for row_class in Rows}


__all__ = "Decimal date Tables load_database save_database load_all clear_all".split()


def load_database(csv_filename=Database_filename):
    r'''Loads the database tables.
    '''
    with open(csv_filename, 'r') as f:
        reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        ans = {}
        while True:
            try:
                header = next(reader)
                assert len(header) == 1, f"from_csv: Expected table name, got {row=}"
                ans[header[0].strip()] = Tables[header[0].strip()].from_csv(reader)
            except StopIteration:
                break
    return ans

def save_database(csv_filename=Database_filename):
    with open(csv_filename, 'w') as f:
        for table in Tables.values():
            table.to_csv(f)

def load_all(from_scratch=True):
    for table in Tables.values():
        if os.path.exists(f"{table.name}.csv"):
            print("loading:", table.name)
            table.load_csv(from_scratch=from_scratch)
        else:
            print("load_all: skipping", table.name)

def clear_all():
    for table in reversed(Tables.values()):
        table.clear()


def run():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", "-i", action="store_true", default=False)
    parser.add_argument("--load", "-l", default=None)
    parser.add_argument("--load-all", "-a", action="store_true", default=False)

    args = parser.parse_args()

    if args.init:
        # create empty database csv file.
        clear_all()
    if args.load_all:
        load_all(from_scratch=True)
    elif args.load is not None:
        Tables[args.load].load_csv(from_scratch=True)

    save_database()



if __name__ == "__main__":
    run()

