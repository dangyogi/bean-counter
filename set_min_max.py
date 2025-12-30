# set_min_max.py

r'''
    - create next Month, with start_date == prior month end_date + 1,
      set min_order, max_perishable, min_non_perishable2.
    - min_order = 1.35 (to 1.40) * new month's.avg_meals_served
    - max_perishable = 0.90 * (new month's.avg_meals_served + next month's.avg_meals_served)
    - min_non_perishable2 = 1.2 * (new month's.avg_meals_served + next month's.avg_meals_served)
    - verify numbers
    - write to Months
'''

from database import *


def run():
    today = date.today()

    load_database()

    cur_month = Months.last_month()

    served_fudge = 1.35

    cur_avg_served = Months.avg_meals_served(cur_month.month)

    while True:
        print(f"avg_served={cur_avg_served}, {served_fudge=} -> min_order={round(served_fudge * cur_avg_served)}")
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
