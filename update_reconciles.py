# update_reconciles.py

r'''
  - read rows into Reconcile table
  - record "monthly", "initial balance" in Reconcile table for today
  - figure out "monthly", "cash out" and "cash in" and record in Reconcile for today
  - record "monthly", "final balance" in Reconcile table for today
  - set end-date to today in Months
  - print out initial bill counts and total
  - print out "cash out" and total
  - print out "cash in" and total
  - print out final bill counts and total
'''

from datetime import date, timedelta
from collections import defaultdict
import math
import sys

from database import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("reconcile_csv_file", nargs='?', default=None)

    args = parser.parse_args()

    load_database()
    if args.reconcile_csv_file is not None:
        load_csv(args.reconcile_csv_file)

    today = date.today()

    # find final balance from last month
    if (today.year, today.month) in Months:
        month = Months[today.year, today.month]
    elif today.day < 15:
        if today.month == 1:
            month = Months[today.year - 1, 12]
        else: 
            month = Months[today.year, today.month - 1]
    start_date = month.start_date - timedelta(days=1)
    start_index = Reconcile.first_date(start_date)
    print(f"{start_date=}, {start_index=}")
    error_msg = f"{start_date.strftime('%b %d, %y')}, monthly, final balance not found in Reconcile"
    initial_balance = None
    bf_revenue = defaultdict(Decimal)
    bf_expenses = defaultdict(Decimal)
    other_revenue = defaultdict(Decimal)
    other_expenses = defaultdict(Decimal)
    for i in range(start_index, len(Reconcile)):
        recon = Reconcile[i]
        print(f"{i=} {initial_balance is None=} {recon.date=}, {recon.event=}, {recon.category=}")
        if initial_balance is None:
            assert recon.date == start_date, error_msg
            if recon.event == 'monthly' and recon.category == 'final balance':
                print("found initial balance")
                initial_balance = recon.copy()
                prev_month = initial_balance.copy()
            else:
                continue
        category_key = recon.event, recon.category
        recon_amount = None
        if recon.type == "income":
            initial_balance += recon
            recon_amount = recon.total
            if category_key + ("start",) in Starts:
                initial_balance -= Starts[category_key + ("start",)]
                recon_amount -= Starts[category_key + ("start",)].total
        elif recon.type == "expense":
            assert recon.donations == 0, \
                   f"unexpected donations={recon.donations} on {recon.event}, {recon.category} expense"
            initial_balance -= recon
            recon_amount = recon.total
        else:
            assert recon.type is None, f"Reconcile row {i} has unknown type {recon.type}"
        if recon_amount is not None:
            if recon.donations:
                report_categories[category_key] += recon_amount - recon.donations
                report_categories[recon.event, "donations"] += recon.donations
            else:
                report_categories[category_key] += recon_amount
    assert initial_balance is not None, error_msg

    month.end_date = today

    # insert monthly initial balance
    Reconcile.insert(date=today, event="monthy", category="initial balance", **initial_balance.as_attrs())

    starts = bills()
    for start in Starts.values():
        if start.detail in ('start', 'petty cash'):
            starts += start

    target = initial_balance - starts

    cash_out = bills()
    cash_in = bills()

    ending_minimums = Starts["monthly", "final balance", "ending minimums"]

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
    Reconcile.insert(date=today, event="monthly", category="cash out", **cash_out.as_attrs())
    Reconcile.insert(date=today, event="monthly", category="cash in", **cash_in.as_attrs())

    final_balance = initial_balance - cash_out + cash_in
    assert initial_balance.total == final_balance.total, f"{initial_balance.total=} != {final_balance.total=}"
    Reconcile.insert(date=today, event="monthly", category="final balance", **final_balance.as_attrs())

    print("            | coin| b1| b5|b10|b20|b50|b100|   total")
    print("prev month  ", end='')
    prev_month.print(file=sys.stdout)
    print("init bal    ", end='')
    initial_balance.print(file=sys.stdout)
    print("cash out    ", end='')
    cash_out.print(file=sys.stdout)
    print("cash in     ", end='')
    cash_in.print(file=sys.stdout)
    print("final bal   ", end='')
    final_balance.print(file=sys.stdout)
    print("minimums    ", end='')
    ending_minimums.print(file=sys.stdout)
    target = final_balance - starts
    print("after starts", end='')
    target.print(file=sys.stdout)

    print()
    print("starts + petty cash:", starts.total)
    print("income for the month:", final_balance.total - prev_month.total)

    if not args.trial_run:
        save_database()

    # print Treasurer's Report
    report = Report("T-Report",
                    title=(Centered(size="title", bold=True),),
                    l0=(Left(bold=True), Mark("m"), Right()),
                    l1=(Left(indent=1, bold=True), "m", Right(indent=1)),
                    l2=(Left(indent=2, bold=True), "m", Right(indent=2)),
                    l3=(Left(indent=3), "m", Right(indent=3)),
                   )

    report.new_row("title").next_cell("Treasurer's Report")
    report.new_row("title").next_cell(f"as of {today.strftime('%b %d, %y')}")
    cash_flow = report.new_row("l0")
    cash_flow.next_cell("Cash Flow")
    total_cash_flow = 0

    breakfast_categories = []  # [category]
    other_categories = []      # [(event, category)]
    for event, category in report_categories.keys():
        if event == "breakfast":
            breakfast_categories.append(category)
        else:
            other_categories.append((event, category))

    breakfast = report.new_row("l1")
    breakfast.next_cell("Breakfast")
    tickets_claimed = Months[today.month(), today.year()].tickets_claimed
    breakfast.set_text2(f"({tickets_claimed} showed up)")

    revenue = report.new_row("l2")
    revenue.next_cell("Revenue")

    ticket_sales = report.new_row("l3")
    ticket_sales.next_cell("Ticket Sales")

    fifty_fifty = report.new_row("l3")
    fifty_fifty.next_cell("50/50 Income")

    print("    revenue:")
    tickets_amount = 0
    tickets = 0
    total_revenue = 0
    for category in breakfast_categories:
        if Categories["breakfast", category].type == "income":
            amount = report_categories["breakfast", category]
            total_revenue += amount
            if category.endswith(" tickets"):
                tickets_amount += amount
                tickets += int(math.ceil(tickets_amount / Categories["breakfast", category].ticket_price))
            elif category == "50/50":
                fifty_fifty.next_cell(amount)
            else:
                assert category == "donations", f"Unknown {category=}"
                row = report.new_row("l3")
                row.next_cell("Donations")
                row.next_cell(amount)
    ticket_sales.set_text2(f"({tickets})")
    ticket_sales.next_cell(tickets_amount)
    revenue.next_cell(total_revenue)

    expenses = report.new_row("l2")
    expenses.next_cell("Expenses")

    total_expenses = 0
    for category in breakfast_categories:
        if Categories["breakfast", category].type == "expense":
            total_expenses += report_categories["breakfast", category]
    expenses.next_cell(total_expenses)

    breakfast.next_cell(total_revenue - total_expenses)
    total_cash_flow += total_revenue - total_expenses

    other = None
    revenue = None
    expenses = None

    for event, category in other_categories:
        if Categories[event, category].type == "income":
            if other is None:
                other = report.new_row("l1")
                other.next_cell("Other")
            if revenue is None:
                revenue = report.new_row("l2")
                revenue.next_cell("Revenue")
            amount = report_categories[event, category]
            print("     ", event, amount)

    print("    expenses:")
    for event, category in other_categories:
        if Categories[event, category].type == "expense":
            amount = report_categories[event, category]
            print("     ", event, amount)



if __name__ == "__main__":
    run()
