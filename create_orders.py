# create_orders.py

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--table-size", "-t", type=int, default=6)
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
    max_expected = cur_month.served_fudge * avg_served1

    print(f"cur_month={cur_month.month_str}, avg_served={avg_served1}, served_fudge={cur_month.served_fudge}, "
          f"{max_expected=}, consumed_fudge={cur_month.consumed_fudge}, "
          f"{table_size=}, num_tables={max_expected / table_size}")

    with open("Orders.csv", "w") as f:
        print("Orders", file=f)
        print("item                |qty |supplier|supplier_id|purchased_pkgs|purchased_units|"
              "location|price", file=f)
        for item in Items.values():
            order = item.order(cur_month, table_size, override=True, verbose=verbose)
           #print(f"{item.item=}, {order=}")
            if order:
                print(f"{item.item:20}|{order:4}|        |           |              |               |"
                      "        |", file=f)



if __name__ == "__main__":
    run()

