# est_cost_per_meal.py

r'''
Adds up num_per_serving or num_per_meal / avg_meals_served for each item in Items and multiplies by
price_per_unit.

Prints the sum.  This includes staff served in converting costs per meal to cost per serving.

Does not include 50/50.
'''


from statistics import mean

from database import *


def run():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--table-size", "-t", type=int, default=8)
    parser.add_argument("--verbose", "-v", default="", help="comma seperated item names")

    args = parser.parse_args()

    load_database()

    avg_meals_served = mean(Months.avg_meals_served(mth) for mth in (1,2,3,4,11,12))

    print(f"{avg_meals_served=}")

    cost = 0
    for item in Items.values():
       #print(item.item, item.num_per_serving, item.num_per_meal)
        units_consumed = 0
        if item.num_per_serving:
            units_consumed = item.num_per_serving
        elif item.num_per_meal:
            units_consumed = item.num_per_meal / avg_meals_served
        cost += units_consumed * float(item.product.price_per_unit)

    print()
    print(f"est cost per meal served is {cost:.02f}")
    print()
    print("Excludes 50/50, and includes staff in converting cost/meal to cost/serving")



if __name__ == "__main__":
    run()

