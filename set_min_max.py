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

    last_month = Months.last_month()
    new_year, new_month = Months.inc_month(last_month.year, last_month.month)
    next_year, next_month = Months.inc_month(new_year, new_month)

    print(f"New month {new_month=}, {new_year=}; {next_month=}")

    assert (new_year, new_month) not in Months, f"New Month({new_month=}, {new_year=}) already created"

    attrs = dict(year=new_year, month=new_month,
                 start_date=last_month.end_date + timedelta(days=1))

    new_avg_served = Months.avg_meals_served(new_month)
    next_avg_served = Months.avg_meals_served(next_month)
    attrs["min_order"] = round(1.35 * new_avg_served)   # maybe up to 1.40 *?
    if new_month == 4:
        attrs["max_perishable"] = attrs["min_order"]
        attrs["min_non_perishable2"] = attrs["min_order"]
    else:
        attrs["max_perishable"] = round(0.90 * (new_avg_served + next_avg_served))
        attrs["min_non_perishable2"] = round(1.2 * (new_avg_served + next_avg_served))

    print(f"{new_avg_served=}, {next_avg_served=}")

    all_attrs = "min_order max_perishable min_non_perishable2".split()
    for attr in all_attrs:
        while True:
            ans = input(f"{attr}={attrs[attr]}? ")
            if not ans:
                break
            n = int(ans)
            if abs(attrs[attr] - n) / attrs[attr] > 0.25:
                print(f"{n} seems like a big difference, try again...")
            else:
                attrs[attr] = n

    for attr in all_attrs:
        print(f"{attr}={attrs[attr]}, ", end='')
    print(f"num_tables={round(attrs["min_order"] / 6)}")

    Months.insert(**attrs)

    if input("Save? (y/n) ").lower() == 'y':
        save_database()
        print("saved")
    else:
        print("aborted")



if __name__ == "__main__":
    run()
