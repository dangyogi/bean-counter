# calc_consumed.py

r'''Inserts code="consumed" rows into Inventory table.
'''

import math

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("--table-size", "-s", type=int, default=8)
    parser.add_argument("--uncertainty", "-u", type=float, default=0.20, help="as percent, default 0.20")

    args = parser.parse_args()

    load_database()

    table_size = args.table_size
    uncertainty_pct = args.uncertainty

    today = date.today()
    cur_month = Months[today.year, today.month]

    eff_date = cur_month.breakfast_date
    meals_served = cur_month.meals_served
    assert meals_served is not None, f"You haven't run set_bf_stats for Month {cur_month.month_str}"
    print(f"Calculating consumption of {meals_served=}, {table_size=}, {uncertainty_pct=}, "
          f"effective {eff_date:%b %d, %y}")

    for item in Items.values():
        units_consumed = item.consumed(meals_served, table_size)
        if units_consumed:
            uncertainty = int(math.ceil(units_consumed * uncertainty_pct))
            print(f"Item {item.item}: {units_consumed} consumed, {uncertainty=}")
            Inventory.insert(date=eff_date, item=item.item, code="consumed", num_units=units_consumed,
                             uncertainty=uncertainty)
        else:
            print(f"Item {item.item}: none consumed")

    if not args.trial_run:
        print("Saving Database")
        save_database()
    else:
        print("Trial_run: Database not saved")



if __name__ == "__main__":
    run()
