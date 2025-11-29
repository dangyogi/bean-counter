# write_inv_checklist.py

from operator import attrgetter

from database import *


def run():
    load_database()

    width = 0
    for i in Items.values():
        l = len(i.item)
        if l > width:
            width = l

    with open("inv_checklist.csv", "w") as f:
        print(f"{'item':{width}}|num_pkgs|num_units", file=f)
        for i in sorted(Items.values(), key=attrgetter('item')):
            print(f"{i.item:{width}}|        | ", file=f)



if __name__ == "__main__":
    run()
