# create_orders.py

import math

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--table-size", "-t", type=int, default=8)
    parser.add_argument("--verbose", "-v", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    cur_month = Months.last_month()
    if not cur_month.served_fudge:
        print(f"served_fudge not set in cur_month({cur_month.month_str}), aborting")
        return
    table_size = args.table_size
    verbose = args.verbose

    avg_served1 = Months.avg_meals_served(cur_month.month)
    if cur_month.month == 4:
        avg_served2 = 0
    else:
        next_month = Database.Months.inc_month(cur_month.year, cur_month.month)[1]
        avg_served2 = Database.Months.avg_meals_served(next_month)
    max_served1 = round(cur_month.served_fudge * avg_served1)
    max_served2 = round(cur_month.served_fudge * avg_served2)
    num_tables = int(math.ceil(max_served1 / table_size))

    print(f"cur_month={cur_month.month_str}, {avg_served1=}, served_fudge={cur_month.served_fudge}, "
          f"{max_served1=}, consumed_fudge={cur_month.consumed_fudge}, "
          f"{table_size=}, {num_tables=}")

    with open("Month_stats.csv", "w") as f:
        print("Month_stats", file=f)
        print("month|max_served1|max_served2|served_fudge|avg_served1|avg_served2|num_tables|table_size|"
              "consumed_fudge", file=f) 
        print(f"{abbr_month(cur_month.month):5}|{max_served1:11}|{max_served2:11}|{cur_month.served_fudge:12.2}|"
              f"{avg_served1:11}|{avg_served2:11}|{num_tables:10}|{table_size:10}|"
              f"{cur_month.consumed_fudge:14.2}", file=f) 

    with (open("Order_stats.csv", "w") as stats_file,
          open("Orders.csv", "w") as orders_file
    ):
        print("Order_stats", file=stats_file)
        print("item                |unit         |pkg_sz|perish|   inv|uncer|cons1|cons2|" \
              "min1|max_order|min2|min3|order", file=stats_file)

        print("Orders", file=orders_file)
        print("item                |qty |supplier|supplier_id|purchased_pkgs|purchased_units|"
              "location|price", file=orders_file)
        for item in Items.values():
            order_stats = item.order_stats(cur_month, table_size, override=True, verbose=verbose)
            print(f"{order_stats.item:20}|",
                  f"{order_stats.unit:13}|",
                  f"{order_stats.pkg_size:6}|",
                  f"{order_stats.perishable:6}|",
                  f"{order_stats.inv:6}|",
                  f"{order_stats.uncertainty:5}|",
                  f"{order_stats.consumed1:5}|"
                  f"{order_stats.consumed2:5}|"
                  f"{order_stats.min_needed1:4}|",
                  sep='', end='', file=stats_file)
            max_order = order_stats.max_order or ""
            min_needed2 = order_stats.min_needed2 or ""
            min_needed3 = order_stats.min_needed3 or ""
            print(f"{max_order:9}|",
                  f"{min_needed2:4}|",
                  f"{min_needed3:4}|",
                  f"{order_stats.order:5}",
                  sep='', file=stats_file)
           #print(f"{item.item=}, {order=}")
            if order_stats.order:
                print(f"{order_stats.item:20}|{order_stats.order:4}|        |           |"
                      "              |               |        |", file=orders_file)



if __name__ == "__main__":
    run()

