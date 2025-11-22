# update_reconciles.py

r'''
  - read rows into Reconcile table
  - record "monthly", "initial balance" in Reconcile table for today
  - figure out "monthly", "cash out" and "cash in" and record in Reconcile for today
  - record "monthly", "final balance" in Reconcile table for today
  - set end-date to today in Months
  - print out initial bill counts and total
  - print out "cash out" and total
  - print out "cash in" and total
  - print out final bill counts and total
'''

from datetime import date, timedelta
from collections import defaultdict
import math
import sys

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("reconcile_csv_file", nargs='?', default=None)

    args = parser.parse_args()

    load_database()
    if args.reconcile_csv_file is not None:
        load_csv(args.reconcile_csv_file)

    today = date.today()

    # find final balance from last month
    if (today.year, today.month) in Months:
        month = Months[today.year, today.month]
    elif today.day < 15:
        if today.month == 1:
            month = Months[today.year - 1, 12]
        else: 
            month = Months[today.year, today.month - 1]
    start_date = month.start_date - timedelta(days=1)
    start_index = Reconcile.first_date(start_date)
    print(f"{start_date=}, {start_index=}")
    error_msg = f"{start_date.strftime('%b %d, %y')}, monthly, final balance not found in Reconcile"
    initial_balance = None
    report_categories = defaultdict(bills)
    for i in range(start_index, len(Reconcile)):
        recon = Reconcile[i]
        print(f"{i=} {initial_balance is None=} {recon.date=}, {recon.event=}, {recon.category=}")
        if initial_balance is None:
            assert recon.date == start_date, error_msg
            if recon.event == 'monthly' and recon.category == 'final balance':
                print("found initial balance")
                initial_balance = recon.copy()
            else:
                continue
        category_key = recon.event, recon.category
        if recon.type == "income":
            initial_balance += recon
            if category_key + ("start",) in Starts:
                initial_balance -= Starts[category_key + ("start",)]
        elif recon.type == "expense":
            initial_balance -= recon
        else:
            assert recon.type is None, f"Reconcile row {i} has unknown type {recon.type}"
        if recon.type is not None:
            report_categories[category_key] += recon
    assert initial_balance is not None, error_msg

    month.end_date = today

    # insert monthly initial balance
    Reconcile.insert(date=today, event="monthy", category="initial balance", **initial_balance.as_attrs())

    target = initial_balance.copy()
    for start in Starts.values():
        if start.detail in ('start', 'petty cash'):
            target -= start

    cash_out = bills()
    cash_in = bills()

    ending_minimums = Starts["monthly", "final balance", "ending minimums"]

    attrs = tuple(target.types.keys())

    # rob from high bills to fill short bills
    for i in range(len(attrs) - 1):
        key = attrs[i]
        target_value = getattr(target, key) - getattr(cash_out, key)
        minimum_value = getattr(ending_minimums, key)
        if target_value < minimum_value:
            i2 = i + 1
            next_key = attrs[i2]
            while bills.value(next_key) % bills.value(key):
                i2 += 1
                next_key = attrs[i2]
            ratio = bills.value(next_key) / bills.value(key)
            assert ratio.is_integer(), f"expected integer ratio, got {ratio=}"
            ratio = int(ratio)
            transfer = math.ceil((minimum_value - target_value) / ratio)
            cash_out.add_to_attr(next_key, transfer)
            cash_in.add_to_attr(key, ratio * transfer)

    # convert lower bills to higher bills
    for i in range(len(attrs) - 1):
        key = attrs[i]
        target_value = getattr(target, key) - getattr(cash_out, key) + getattr(cash_in, key)
        minimum_value = getattr(ending_minimums, key)
        if target_value > minimum_value:
            i2 = i + 1
            next_key = attrs[i2]
            while bills.value(next_key) % bills.value(key):
                i2 += 1
                next_key = attrs[i2]
            ratio = bills.value(next_key) / bills.value(key)
            assert ratio.is_integer(), f"expected integer ratio, got {ratio=}"
            ratio = int(ratio)
            transfer = math.floor((target_value - minimum_value) / ratio)
            cash_out.add_to_attr(key, ratio * transfer)
            cash_in.add_to_attr(next_key, transfer)
            if key == 'b20':
                # can we combine 2 20s and 1 10 to get a 50?
                target_value = getattr(target, key) - getattr(cash_out, key) + getattr(cash_in, key)
                transfer = math.floor((target_value - minimum_value) / 2)
                extra_b10s = (target.b10 - cash_out.b10 + cash_in.b10) - ending_minimums.b10
                if extra_b10s > 0:
                    t = min(transfer, extra_b10s)
                    cash_out.b20 += 2*t
                    cash_out.b10 += t
                    cash_in.b50 += t

    # normalize cash_out against cash_in for each bill
    for bill in "coin b1 b5 b10 b20 b50 b100".split():
        if getattr(cash_out, bill) > getattr(cash_in, bill):
            cash_out.sub_from_attr(bill, cash_in)
            setattr(cash_in, bill, 0)
        elif getattr(cash_in, bill) > getattr(cash_out, bill):
            cash_in.sub_from_attr(bill, cash_out)
            setattr(cash_out, bill, 0)

    assert cash_in.total == cash_out.total, f"{cash_in.total=} != {cash_out.total=}"
    Reconcile.insert(date=today, event="monthly", category="cash out", **cash_out.as_attrs())
    Reconcile.insert(date=today, event="monthly", category="cash in", **cash_in.as_attrs())

    final_balance = initial_balance - cash_out + cash_in
    Reconcile.insert(date=today, event="monthly", category="final balance", **final_balance.as_attrs())

    print("            | coin| b1| b5|b10|b20|b50|b100|   total")
    print("init bal    ", end='')
    initial_balance.print(file=sys.stdout)
    print("cash out    ", end='')
    cash_out.print(file=sys.stdout)
    print("cash in     ", end='')
    cash_in.print(file=sys.stdout)
    print("final bal   ", end='')
    final_balance.print(file=sys.stdout)
    print("minimums    ", end='')
    ending_minimums.print(file=sys.stdout)
    target = final_balance.copy()
    for start in Starts.values():
        if start.detail in ('start', 'petty cash'):
            target -= start
    print("after starts", end='')
    target.print(file=sys.stdout)

    if not args.trial_run:
        save_database()



if __name__ == "__main__":
    run()
