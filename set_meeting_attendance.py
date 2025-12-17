# set_meeting_attendance.py

r'''Stores num_at_meeting in current Month.
'''

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("attendance", type=int)

    args = parser.parse_args()

    today = date.today()

    load_database()

    cur_month = Months[today.year, today.month]

    print("Setting num_at_meeting to", args.attendance)
    cur_month.num_at_meeting = args.attendance

    save_database()
    print("Database saved")



if __name__ == "__main__":
    run()
