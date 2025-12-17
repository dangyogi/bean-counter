# record_purchases.py

r'''
  - add "purchased" rows to Inventory table
  - update location and price in Products
  # write receipt slips (computer figures out bills?)
  #   -- don't have price paid, might go to two different people...
'''

from datetime import date

from database import *

def run():
    import argparse

    today = date.today()

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("--month", "-m", type=int, default=today.month)
    parser.add_argument("--day", "-d", type=int, default=today.day)
    parser.add_argument("--year", "-y", type=int, default=today.year)
    parser.add_argument("orders_csv_file", nargs='?', default="Orders.csv")

    args = parser.parse_args()

    load_database()
    load_csv(args.orders_csv_file)

    year = args.year
    month = args.month
    day = args.day

    if month > today.month:
        year -= 1
    elif day > today.day:
        year, month = Months.dec_month(year, month)

    eff_date = date(year, month, day)
    print(f"Effective date {eff_date:%b %d, %y}")

    for order in Orders.values():
        assert order.item in Items, f"{order.item=} not in Items table"
        attrs = dict(date=eff_date, item=order.item, code="purchased")
        if order.purchased_pkgs is not None:
            attrs["num_pkgs"] = order.purchased_pkgs
        elif order.qty is not None:
            attrs["num_pkgs"] = order.qty
        if order.purchased_units is not None:
            attrs["num_units"] = order.purchased_units
        Inventory.insert(**attrs)
        if order.location is not None:
            print(f"Updating Product[{order.product.item}, {order.product.supplier}, "
                                   f"{order.product.supplier_id}].location to", order.location)
            order.product.location = order.location
        if order.price is not None:
            print(f"Updating Product[{order.product.item}, {order.product.supplier}, "
                                   f"{order.product.supplier_id}].price to", order.price)
            order.product.price = order.price

    if not args.trial_run:
        print("Saving Database")
        save_database()
    else:
        print("Trial_run: Database not saved")



if __name__ == "__main__":
    run()
