# read_inv.py

import csv

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--code", "-c", default="count")
    parser.add_argument("--date", "-d", default=date.today().strftime("%b %d, %y"))
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)

    args = parser.parse_args()

    args.date
    args.code

    print(f"Loading inv_checklist.csv with {args.date=} and {args.code=}")

    load_database()

    with open("inv_checklist.csv", "r") as f:
        csv_reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        headers = next(csv_reader)
        for row in csv_reader:
            assert len(headers) == len(row), f"{len(headers)=} != {len(row)=}"
            Inventory.add_row(Inventory.row_class.from_csv(["date", "code"] + headers,
                                                           [args.date, args.code] + row))

    if not args.trial_run:
        save_database()
        print("Database saved")
    else:
        print("Database not saved")



if __name__ == "__main__":
    run()
