# set_min_max.py

r'''
    - create next Month, with start_date == prior month end_date + 1, set min_order, max_perishable, max_non_perishable
    - min_order = 1.35 (to 1.40) * new month's.avg_meals_served
    - max_perishable = 0.90 * (new month's.avg_meals_served + next month's.avg_meals_served)
    - max_non_perishable = 0.80 * (sum of new month and next 2 months.avg_meals.served)
    - verify numbers
    - write to Months
'''

from database import *


def run():
    today = date.today()

    load_database()

    cur_year = today.year
    cur_month = today.month
    
    if today.day > 12:
        if cur_month == 12:
            new_year = cur_year + 1
            new_month = 1
        else:
            new_year = cur_year
            new_month = cur_month + 1
    else:
        new_year = cur_year
        new_month = cur_month
        if new_month == 1:
            cur_year = new_year - 1
            cur_month = 12
        else:
            cur_month = new_month - 1


    if new_month == 12:
        next_month = 1
    else:
        next_month = new_month + 1

    if next_month == 12:
        next_month_2 = 1
    else:
        next_month_2 = next_month + 1

    print(f"New month {new_month=}, {new_year=}; {next_month=}, {next_month_2=}")

    assert (cur_year, cur_month) in Months, f"Cur Month({cur_month=}, {cur_year=}) doesn't exist in Months"
    assert (new_year, new_month) not in Months, f"New Month({new_month=}, {new_year=}) already created"

    attrs = dict(year=new_year, month=new_month,
                 start_date=Months[cur_year, cur_month].end_date + timedelta(days=1))

    new_avg_served = Months.avg_meals_served(new_month)
    next_avg_served = Months.avg_meals_served(next_month)
    next2_avg_served = Months.avg_meals_served(next_month_2)
    attrs["min_order"] = round(1.35 * new_avg_served)   # maybe up to 1.40 *?
    if new_month == 4:
        attrs["max_perishable"] = attrs["min_order"]
        attrs["max_non_perishable"] = attrs["min_order"]
    else:
        attrs["max_perishable"] = round(0.90 * (new_avg_served + next_avg_served))
        if new_month == 3:
            attrs["max_non_perishable"] = attrs["max_perishable"]
        else:
            attrs["max_non_perishable"] = round(0.80 * (new_avg_served + next_avg_served + next2_avg_served))

    print(f"{new_avg_served=}, {next_avg_served=}, {next2_avg_served=}")

    all_attrs = "min_order max_perishable max_non_perishable".split()
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
