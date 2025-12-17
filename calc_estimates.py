# calc_estimates.py

r'''Inserts code="estimate" rows into Inventory table.
'''

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("--verbose", "-v", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    today = date.today()
    cur_month = Months[today.year, today.month]

    print(f"Calculating estimates effective {today:%b %d, %y}")

    for item in Items.values():
        units, uncertainty = item.in_stock(args.verbose)
        if args.verbose:
            print(f"Item {item.item}: {units=}, {uncertainty=}")
        Inventory.insert(date=today, item=item.item, code="estimate", num_units=units,
                         uncertainty=uncertainty)

    if not args.trial_run:
        print("Saving Database")
        save_database()
    else:
        print("Trial_run: Database not saved")



if __name__ == "__main__":
    run()
