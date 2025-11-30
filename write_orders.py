# write_orders.py

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--table-size", "-t", type=int, default=6)
    parser.add_argument("--verbose", "-v", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    last_month = Months.last_month()
    if not last_month.served_fudge:
        print(f"served_fudge not set in last_month({last_month.month_str}), aborting")
        return
    table_size = args.table_size
    verbose = args.verbose

    print(f"last_month={last_month.month_str}, served_fudge={last_month.served_fudge}, "
          f"consumed_fudge={last_month.consumed_fudge}, "
          f"{table_size=}")

    with open("Orders.csv", "w") as f:
        print("item                |qty |supplier|supplier_id|purchased_pkgs|purchased_units|"
              "location|price", file=f)
        for item in Items.values():
            order = item.order(last_month, table_size, verbose)
           #print(f"{item.item=}, {order=}")
            if order:
                print(f"{item.item:20}|{order:4}|        |           |              |               |"
                      "        |", file=f)



if __name__ == "__main__":
    run()

