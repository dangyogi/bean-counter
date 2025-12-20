# create_inv_checklist.py

r'''
    - update Inventory table by writing new  "estimate" rows.
    - calc orders
    - expected_count = cur_count + order
    - uncertainty = 0.10 * sum of consumed since last count
    - write all items that have expected_count - uncertainty < min
      or if perishable, expected_count + uncertainty > max_perishable
'''

# FIX: only include items that need to be counted

from operator import attrgetter

from database import *


def run():
    load_database()

    width = 0
    for i in Items.values():
        l = len(i.item)
        if l > width:
            width = l

    with open("Inv-checklist.csv", "w") as f:
        print(f"{'item':{width}}|num_pkgs|num_units", file=f)
        for i in sorted(Items.values(), key=attrgetter('item')):
            print(f"{i.item:{width}}|        | ", file=f)



if __name__ == "__main__":
    run()
