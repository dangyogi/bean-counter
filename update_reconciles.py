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
from report import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-run", "-t", action="store_true", default=False)
    parser.add_argument("--pdf", "-p", action="store_true", default=False)
    parser.add_argument("reconcile_csv_file", nargs='?', default=None)

    args = parser.parse_args()

    load_database()
    if args.reconcile_csv_file is not None:
        load_csv(args.reconcile_csv_file)

    today = date.today()

    # Get the cur_month from Months:
    if (today.year, today.month) in Months:
        cur_month = Months[today.year, today.month]
    elif today.day < 15:
        # Backup to month before today...
        year_month = cur_month.prev_month
        cur_month = Months[year_month]

    # Find our initial_balance in the Reconcile table.
    start_date = cur_month.start_date - timedelta(days=1)   # backup 1 day from the cur_month.start_date.
                                                            # this should be the prior month's end_date.
    start_index = Reconcile.first_date(start_date)          # find the start_index into Reconcile for start_date
    print(f"{start_date=}, {start_index=}")
    error_msg = f"{start_date.strftime('%b %d, %y')}, monthly, final balance not found in Reconcile"
    initial_balance = None
    first_transfer = None
    # This same loop is used to both find the initial_balance, and to process the remaining rows in Reconcile.
    for i in range(start_index, len(Reconcile)):  # loop from start_index to the end of Reconcile
        recon = Reconcile[i]
        if initial_balance is None:
            # Still looking for initial_balance...
            assert recon.date == start_date, error_msg
            if recon.event == 'monthly' and recon.category == 'final balance':
                print("found initial balance")
                initial_balance = recon.copy()
                prev_month = initial_balance.copy()
            else:
                # Don't do anything until we find our initial_balance...
                continue

        if first_transfer is None:
            first_transfer = i      # for later,  creating the Treasurer's Report

        # OK, We've got our starting initial_balance (copied into prev_month for safe keeping).
        # We need to update the initial_balance with what went in or out.
        print(f"{i=} date={recon.date:%m %d, %y} event={recon.event} category={recon.category} type={recon.type} total={recon.total}")
        if recon.type == "income":
            initial_balance += recon
            if (recon.event, recon.category, "start",) in Starts:
                initial_balance -= Starts[(recon.event, recon.category, "start")]
        elif recon.type == "expense":
            assert recon.donations == 0, \
                   f"unexpected donations={recon.donations} on {recon.event}, {recon.category} expense"
            initial_balance -= recon
        else:
            assert recon.type is None, f"Reconcile row {i} has unknown type {recon.type}"
    assert initial_balance is not None, error_msg

    # Now initial_balance should reflect our current cash, before the cash swap.

    # FIX: Add this step to cur_month
    cur_month.end_date = today

    # insert monthly initial balance
    Reconcile.insert(date=today, event="monthy", category="initial balance", **initial_balance.as_attrs())

    # Figure out the cash exchange:
    starts = bills()
    for start in Starts.values():
        if start.detail in ('start', 'petty cash'):
            starts += start

    target = initial_balance - starts   # ending_minimums don't include starts...

    ending_minimums = Starts["monthly", "final balance", "ending minimums"]

    # Figure out cash_out and cash_in:
    cash_out = bills()
    cash_in = bills()

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

    # OK, now we have the calculated cash_out and cash_in!

    Reconcile.insert(date=today, event="monthly", category="cash out", **cash_out.as_attrs())
    Reconcile.insert(date=today, event="monthly", category="cash in", **cash_in.as_attrs())

    # Figure out what our final_balance is:
    final_balance = initial_balance - cash_out + cash_in
    assert initial_balance.total == final_balance.total, f"{initial_balance.total=} != {final_balance.total=}"

    Reconcile.insert(date=today, event="monthly", category="final balance", **final_balance.as_attrs())

    # Give the user the results:
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
    target = final_balance - starts
    print("w/out starts", end='')
    target.print(file=sys.stdout)
    print("minimums    ", end='')
    ending_minimums.print(file=sys.stdout)

    print()
    print("starts + petty cash:", starts.total)
    print("income for the month:", final_balance.total - prev_month.total)

    if not args.trial_run:
        save_database()

    # print Treasurer's Report
    report = Report("T-Report",
                    title=(Centered(span=2, size="title", bold=True),),
                    l0=(Left(bold=True), Right(text_format="{:.2f}")),
                    l1=(Left(indent=1, bold=True), Right(indent=1, text_format="{:.2f}")),
                    l2=(Left(indent=2, bold=True), Right(indent=2, text_format="{:.2f}")),
                    l3=(Left(indent=3), Right(indent=3, text_format="{:.2f}")),
                   )

    report.new_row("title", "Treasurer's Report")
    report.new_row("title", f"as of {today.strftime('%b %d, %y')}", size=report.default_size)

    cash_flow_section = Row_template("l0", "Cash Flow",
                  bf :=     Row_template("l1", "Breakfast",
              bf_rev :=         Row_template("l2", "Revenue",
        ticket_sales :=             Row_template("l3", "Breakfast Ticket Sales", text2_format="({})"),
            bf_50_50 :=             Row_template("l3", "50/50 Income"),
        bf_donations :=             Row_template("l3", "Donations"),
                                ),
              bf_exp :=         Row_template("l2", "Expenses", invert_parent=True),
                                text2_format="({}) showed up",
                            ),
                            Row_template("l1", "Other",
           other_rev :=         Row_template("l2", "Revenue"),
           other_exp :=         Row_template("l2", "Expenses", invert_parent=True),
                            ),
                        )

    prev_yr, prev_mth = cur_month.prev_month
    prev_month_str = f"{abbr_month(prev_mth)} '{str(prev_yr)[2:]}"

    balance_section = Row_template("l0", "Balance",
                            Row_template("l1", "Expected Balance",
            prev_bal :=         Row_template("l2", "Previous Balance", text2_format=prev_month_str),
               eb_cf :=         Row_template("l2", "Cash Flow"),
                            ),
                            Row_template("l1", "Current Balance",
                bank :=         Row_template("l2", "Bank", force=True),
                cash :=         Row_template("l2", "Cash"),
                            ),
                        )

    cash_flow_section.add_parent(eb_cf)
    prev_bal += prev_month.total
    cash += final_balance.total
    bf.inc_text2_value(cur_month.tickets_claimed)

    other_revenue = defaultdict(int)   # {event: total}
    other_expenses = defaultdict(int)  # {event: total}
    for i in range(first_transfer, len(Reconcile)):  # loop from start_index to the end of Reconcile
        recon = Reconcile[i]
        if recon.event == "breakfast":
            if recon.type == "income":
                match recon.category:
                    case "adv tickets" | "door tickets":
                        ticket_sales += recon.total
                        if (recon.event, recon.category, "start",) in Starts:
                            ticket_sales -= Starts[(recon.event, recon.category, "start")].total
                        ticket_sales.inc_text2_value(recon.tickets_sold)
                        bf_donations += recon.donations
                    case "50/50":
                        bf_50_50 += recon.total
                        if (recon.event, recon.category, "start",) in Starts:
                            bf_50_50 -= Starts[(recon.event, recon.category, "start")].total
                    case "donations":
                        bf_donations += recon.total
            elif recon.type == "expense":
                bf_exp += recon.total
        else:
            if recon.category in ("income",):
                other_revenue[recon.event] += recon.total
                other_revenue["donations"] += recon.donations
            elif recon.category in ("donation", "reimbursement", "expense"):
                other_expenses[recon.event] += recon.total

    for key, value in other_revenue.items():
        other_rev.add_child(rt := Row_template("l3", key))
        rt += value

    for key, value in other_expenses.items():
        other_exp.add_child(rt := Row_template("l3", key))
        rt += value

    cash_flow_section.insert(report)
    balance_section.insert(report)

    if args.pdf:
        report.draw_init()
        report.draw()
        report.canvas.showPage()
        report.canvas.save()
    else:
        report.print_init()
        report.print()



if __name__ == "__main__":
    run()
