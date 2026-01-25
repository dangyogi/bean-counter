# set_min_max.py

r'''
    - cur_month is last_month
    - ask for served_fudge (starting at 1.35): min_order = served_fudge * cur_month's.avg_meals_served
    - set served_fudge
    - ask for consumed_fudge (starting at 0.9)
    - set consumed_fudge
    - ask whether to save database
    - if yes, save database
'''

from database import *


def run():
    today = date.today()

    load_database()

    cur_month = Months.last_month()

    served_fudge = 1.35

    cur_avg_served = Months.avg_meals_served(cur_month.month)

    while True:
        print(f"cur_month={cur_month.month_str}: avg_served={cur_avg_served}, {served_fudge=}, -> min_order={round(served_fudge * cur_avg_served)}")
        # maybe up to 1.40 *?
        ans = input(f"{served_fudge=}? ")
        if not ans:
            break
        n = float(ans)
        if abs(served_fudge - n) / served_fudge > 0.25:
            print(f"{n} seems like a big difference, try again...")
        else:
            served_fudge = n

    cur_month.served_fudge = served_fudge

    consumed_fudge = 0.9

    while True:
        print(f"{consumed_fudge=}")
        ans = input(f"{consumed_fudge=}? ")
        if not ans:
            break
        n = float(ans)
        if abs(consumed_fudge - n) / consumed_fudge > 0.25:
            print(f"{n} seems like a big difference, try again...")
        else:
            consumed_fudge = n

    cur_month.consumed_fudge = consumed_fudge

   #print(f"num_tables={round(attrs["min_order"] / 6)}")

    if input("Save? (y/n) ").lower() == 'y':
        print("Saving database")
        save_database()
    else:
        print("Database not saved")



if __name__ == "__main__":
    run()
