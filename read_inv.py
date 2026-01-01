# read_inv.py

r'''Loads Inv-checklist.csv into Transactions table.
'''

import csv

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
        header_map = dict((name, i) for i, name in enumerate(headers))  # {name: index}
        for capture_header in capture_headers:
            assert capture_header in header_map, f"{capture_header=} not in header_map={tuple(header_map.keys())}"
        for row in csv_reader:
            assert len(headers) == len(row), f"{len(headers)=} != {len(row)=}"
            Inventory.insert_from_csv(["date", "code"] + capture_headers,
                                      [args.date, args.code] + [row[header_map[capture_header]]
                                                                for capture_header in capture_headers])

    if not args.trial_run:
        save_database()
        # FIX: Truncate Inv-checklist.csv
        print("Database saved")
    else:
        print("Trial_run: Database not saved")



if __name__ == "__main__":
    run()
