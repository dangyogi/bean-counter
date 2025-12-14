# cash_balance.py

r'''Appends to Reconcile table:

   <today>|cash|w/o starts|...
   <today>|cash|w/starts  |...
'''

from datetime import date
import sys

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    today = date.today()

    for i, recon in enumerate(reversed(Reconcile)):
        if recon.account == 'cash' and recon.detail == 'w/starts':
            balance = recon.copy()
            next = len(Reconcile) - i - 1
            break
    else:
        raise AssertionError('"cash", "w/start" not found in Reconcile')

    for recon in Reconcile[next:]:
        if recon.type == "income":
            balance += recon
            if (recon.account, "start",) in Starts:
                balance -= Starts[(recon.account, "start")]
        elif recon.type == "expense":
            assert recon.donations == 0, \
                   f"unexpected donations={recon.donations} on {recon.date:%b %d, %y}, {recon.account}, " \
                   f"{recon.detail} expense"
            balance -= recon
        else:
            assert recon.type is None, \
                   f"Reconcile row {recon.date:%b %d, %y}, {recon.account} has unknown type {recon.type}"

    # Now balance should reflect our current cash, w/starts
    balance_no_starts = balance.copy()

    # Figure out the cash exchange:
    starts = bills()
    for start in Starts.values():
        if start.detail == 'start':
            balance_no_starts -= start

    # insert monthly initial balance
    Reconcile.insert(date=today, account="cash", detail="w/o starts", **balance_no_starts.as_attrs())
    Reconcile.insert(date=today, account="cash", detail="w/starts", **balance.as_attrs())

    # Give the user the results:
    print("date      |account|detail    | coin| b1| b5|b10|b20|b50|b100|   total")
    print(f"{today:%b %d, %y}|cash   |w/o starts", end='')
    balance_no_starts.print(file=sys.stdout)
    print(f"{today:%b %d, %y}|cash   |w/starts  ", end='')
    balance.print(file=sys.stdout)

    if not args.trial_run:
        save_database()



if __name__ == "__main__":
    run()
