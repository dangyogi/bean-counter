# create_inv_checklist.py

r'''
    - update Inventory table by writing new  "estimate" rows.
    - calc orders
    - expected_count = cur_count + order
    - uncertainty = 0.10 * sum of consumed since last count
    - write all items that have expected_count + uncertainty > max_perishable
'''

# FIX: only include items that need to be counted

from operator import attrgetter

from database import *


def run():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--table-size", "-t", type=int, default=8)
    parser.add_argument("--verbose", "-v", default="", help="comma seperated item names")

    args = parser.parse_args()

    table_size = args.table_size
    verbose = args.verbose.split(',')

    load_database()

    cur_month = list(Months.values())[-1]
    print(f"cur_month={cur_month.month_str}")

    width = 0
    for i in Items.values():
        l = len(i.item)
        if l > width:
            width = l

    with open("Inv-checklist.csv", "w") as f:
        print(f"{'item':{width}}|unit         |pkg_size|num_pkgs|num_units", file=f)
        for i in sorted(Items.values(), key=attrgetter('item')):
            try:
                i.order(cur_month, table_size, verbose=i.item in verbose)
            except CheckInventory:
                print(f"{i.item:{width}}|{i.unit:13}|{i.pkg_size:8}|        | ", file=f)



if __name__ == "__main__":
    run()
