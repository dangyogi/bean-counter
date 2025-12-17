# set_bf_stats.py

r'''Stores staff_at_breakfast and tickets_claimed in current Month.
'''

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("staff", type=int)
    parser.add_argument("tickets_claimed", type=int)

    args = parser.parse_args()

    today = date.today()

    load_database()

    cur_month = Months[today.year, today.month]

    print("Setting staff_at_breakfast to", args.staff)
    cur_month.staff_at_breakfast = args.staff

    print("Setting tickets_claimed to", args.tickets_claimed)
    cur_month.tickets_claimed = args.tickets_claimed

    save_database()
    print("Database saved")



if __name__ == "__main__":
    run()
