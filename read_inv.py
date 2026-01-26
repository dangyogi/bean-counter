# read_inv.py

r'''Loads Inv-checklist.csv into Transactions table.
'''

import csv
from itertools import chain

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--code", "-c", default="count")
    parser.add_argument("--date", "-d", default=date.today().strftime("%b %d, %y"))
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)

    args = parser.parse_args()

    print(f"Loading Inv-checklist.csv with {args.date=} and {args.code=}")

    load_database()

    capture_headers = "item num_pkgs num_units".split()

    with open("Inv-checklist.csv", "r") as f:
        csv_reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        headers = next(csv_reader)
        header_map = dict((name.strip(), i) for i, name in enumerate(headers))  # {name: index}
        for capture_header in capture_headers:
            assert capture_header in header_map, f"{capture_header=} not in header_map={tuple(header_map.keys())}"
        extended_headers = capture_headers + ['units', 'uncertainty']
        extended_widths = [len(header) for header in extended_headers]
        display_rows = []
        for row in csv_reader:
            assert len(headers) == len(row), f"{len(headers)=} != {len(row)=}"
            data = [row[header_map[capture_header]].strip()
                    for capture_header in capture_headers]
            display_row = data + list(Items[data[0]].in_stock())
            extended_widths = [max(len(str(data)), width)
                               for width, data in zip(extended_widths, display_row)]
            display_rows.append(display_row)
            if any(element for element in data[1:]):
                Inventory.insert_from_csv(["date", "code"] + capture_headers,
                                          [args.date, args.code] + data)
            else:
                print(f"No counts for {data[0]}, skipping")
        print('|'.join(f"{header:{width}}" for width, header in zip(extended_widths, extended_headers)))
        for row in display_rows:
            sep = ''
            for header, width, value in zip(extended_headers, extended_widths, row):
                print(f"{sep}{value:{width}}", end='')
                sep = '|'
            print()

    if not args.trial_run:
        save_database()
        # FIX: Truncate Inv-checklist.csv
        print("Database saved")
    else:
        print("Trial_run: Database not saved")



if __name__ == "__main__":
    run()
