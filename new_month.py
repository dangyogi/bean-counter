# new_month.py

r'''Stores num_at_meeting in current Month.
'''

from sys import exit

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("--new-month", "-m", type=int, default=None)
    parser.add_argument("--end-day", "-e", type=int, default=None)

    args = parser.parse_args()
    trial_run = args.trial_run
    new_month = args.new_month
    end_day = args.end_day

    load_database()

    last_month = list(Months.values())[-1]
    print(f"last_month: {last_month.month_str}, ", end='')
    if last_month.end_date is not None:
        print(f"end_date={last_month.end_date:%b %d, %y}")
    else:
        print(f"end_date=None")
        if end_day is None:
            end_date = date.today()
        else:
            end_date = date(last_month.year, last_month.month, end_day)
        print(f"Setting {last_month.month_str}.end_date to {end_date:%b %d, %y}")
        last_month.end_date = end_date
    if new_month is None:
        yr, mth = Months.inc_month(last_month.year, last_month.month)
        if mth == 5:
            print("You must explicitly specify May (month 5) with -m 5")
            exit(1)
    elif new_month < last_month.month:
        yr, mth = last_month.year + 1, new_month
    else:
        yr, mth = last_month.year, new_month
    Months.insert(year=yr, month=mth, start_date=last_month.end_date + timedelta(days=1))
    new_month = Months[yr, mth]
    print(f"Created new_month {new_month.month_str}, start_date={new_month.start_date:%b %d, %y}")

    if not args.trial_run:
        print("Saving Database")
        save_database()
    else:
        print("Trial_run: Database not saved")



if __name__ == "__main__":
    run()
