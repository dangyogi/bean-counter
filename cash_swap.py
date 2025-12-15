# cash_swap.py

r'''
  - figure out "monthly", "cash out" and "cash in" and record in Reconcile for today
  - record "monthly", "final balance" in Reconcile table for today
  - print out initial bill counts and total
  - print out "cash out" and total
  - print out "cash in" and total
  - print out final bill counts and total
'''

from datetime import date
import math
import sys

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    today = date.today()

    last_recon = Reconcile[-1]
    assert last_recon.account == "cash", f'Last Reconcile account must be "cash", not "{last_recon.account}"'
    assert last_recon.detail == "w/starts", f'Last Reconcile detail must be "w/starts", not "{last_recon.detail}"'
    initial_with_starts = last_recon.copy()

    # Figure out the cash exchange:
    starts = bills()
    for start in Starts.values():
        if start.detail == 'start':
            starts += start

    initial_balance = initial_with_starts - starts   # ending_minimums don't include starts...
    target = initial_balance.copy()

    ending_minimums = Starts["cash", "minimums"]

    # Figure out cash_out and cash_in:
    cash_out = bills()
    cash_in = bills()

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

    # OK, now we have the calculated cash_out and cash_in!

    Reconcile.insert(date=today, account="cash", detail="cash out", **cash_out.as_attrs())
    Reconcile.insert(date=today, account="cash", detail="cash in", **cash_in.as_attrs())

    # Figure out what our final_balance is:
    final_no_starts = initial_balance - cash_out + cash_in
    assert initial_balance.total == final_no_starts.total, f"{initial_balance.total=} != {final_no_starts.total=}"

    Reconcile.insert(date=today, account="cash", detail="w/o starts", **final_no_starts.as_attrs())
    final_with_starts = final_no_starts + starts
    Reconcile.insert(date=today, account="cash", detail="w/starts", **final_with_starts.as_attrs())

    # Give the user the results:
    print("                | coin| b1| b5|b10|b20|b50|b100|   total")
    print("have w/o starts ", end='')
    initial_balance.print(file=sys.stdout)
    print("have w/starts   ", end='')
    initial_with_starts.print(file=sys.stdout)
    print("cash out        ", end='')
    cash_out.print(file=sys.stdout)
    print("cash in         ", end='')
    cash_in.print(file=sys.stdout)
    print("final w/o starts", end='')
    final_no_starts.print(file=sys.stdout)
    print("final w/starts  ", end='')
    final_with_starts.print(file=sys.stdout)
    print("minimums        ", end='')
    ending_minimums.print(file=sys.stdout)

    print()
    print("starts + petty cash:", starts.total)

    if not args.trial_run:
        save_database()



if __name__ == "__main__":
    run()
