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

    parser = argparse.ArgumentParser()
    parser.add_argument("order_csv_file")

    args = parser.parse_args()

    load_database()
    load_csv(args.order_csv_file)
    today = date.today()
    for order in Orders.values():
        if order.item in Items:
            attrs = dict(date=today, item=order.item, code="purchased")
            if order.purchased_pkgs is not None:
                attrs["num_pkgs"] = order.purchased_pkgs
            elif order.qty is not None:
                attrs["num_pkgs"] = order.qty
            if order.purchased_units is not None:
                attrs["num_units"] = order.purchased_units
            Inventory.insert(**attrs)
            if order.location is not None:
                order.product.location = order.location
            if order.price is not None:
                order.product.price = order.price
    save_database()


if __name__ == "__main__":
    run()
