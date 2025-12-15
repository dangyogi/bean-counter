# update_reconcile.py

r'''
  - read Reconcile.csv into Reconcile table
  - clears Reconcile.csv
'''

from datetime import date, timedelta
from collections import defaultdict
import math
import sys

from database import *
from report import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("--no-clear", "-n", action="store_true", default=False)
    parser.add_argument("reconcile_csv_file", nargs='?', default=None)

    args = parser.parse_args()

    load_database()
    recon_file = args.reconcile_csv_file or "Reconcile.csv"
    print("Copying", recon_file, "into database")
    load_csv(recon_file, from_scratch=False)

    if not args.trial_run:
        print("Saving database")
        save_database()
        if not args.no_clear:
            while (ans := input(f"Clear {recon_file}? (y) ").lower()) not in ("", "y", "yes", "n", "no"):
                print('Looking for "", "y", "yes", "n" or "no"')
            if ans in ("", "y", "yes"):
                print("Clearing", recon_file)
                with open(recon_file, "r") as file_in:
                    table_name = file_in.readline()
                    headers = file_in.readline()
                with open(recon_file, "w") as file_out:
                    print(table_name, end='', file=file_out)
                    print(headers, end='', file=file_out)
                return
        print("Preserving", recon_file)



if __name__ == "__main__":
    run()
