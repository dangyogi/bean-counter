# write_treasurer_report.py

from datetime import date, timedelta
from collections import defaultdict

from database import *
from report import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--month", "-m", type=int, default=date.today().month)
    parser.add_argument("--pdf", "-p", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    today = date.today()

    year = today.year
    month = args.month
    if today.month < month:
        year -= 1

    cur_month = Months[year, month]
    end_date = cur_month.end_date

    def find_final(end_date):
        r'''Find the final balance in the Reconcile table for end_date.

        Returns index, recon row.
        '''
        start_index = Reconcile.first_date(end_date)   # start_index into Reconcile for end_date
        print(f"{end_date=}, {start_index=}")
        error_msg = f"{end_date.strftime('%b %d, %y')}, monthly, final balance not found in Reconcile"
        for i in range(start_index, len(Reconcile)):  # loop from start_index to the end of Reconcile
            recon = Reconcile[i]
            assert recon.date == end_date, error_msg
            if recon.event == 'monthly' and recon.category == 'final balance':
                print("found final balance")
                return i, recon
        raise AssertionError(error_msg)

    final_index, final_balance = find_final(end_date)

    # print Treasurer's Report
    set_canvas("T-Report")
    report = Report(title=(Centered(span=5, size="title", bold=True),),
                    l0=(Left(bold=True, span=4),           Right(text_format="{:.2f}")),
                    l1=(Left(indent=1, bold=True, span=3), Right(text_format="{:.2f}", skip=1)),
                    l2=(Left(indent=2, bold=True, span=2), Right(text_format="{:.2f}", skip=2)),
                    l3=(Left(indent=3),                    Right(text_format="{:.2f}", skip=3)),
                   )

    report.new_row("title", "Treasurer's Report")
    report.new_row("title", f"as of {end_date.strftime('%b %d, %y')}", size=report.default_size)

    cash_flow_section = Row_template("l0", "Cash Flow",
                  bf :=     Row_template("l1", "Breakfast",
              bf_rev :=         Row_template("l2", "Revenue",
        ticket_sales :=             Row_template("l3", "Breakfast Ticket Sales", text2_format="({})"),
            bf_50_50 :=             Row_template("l3", "50/50 Income"),
        bf_donations :=             Row_template("l3", "Donations"),
                                ),
              bf_exp :=         Row_template("l2", "Expenses", invert_parent=True, pad=5),
                                text2_format="({}) showed up",
                            ),
                            Row_template("l1", "Other",
           other_rev :=         Row_template("l2", "Revenue"),
           other_exp :=         Row_template("l2", "Expenses", invert_parent=True, pad=5),
                                pad=5,
                            ),
                            pad=5,
                        )

    prev_end_date  = cur_month.start_date - timedelta(days=1)
    prev_index, prev_balance = find_final(prev_end_date)

    prev_month_str = f"{abbr_month(prev_end_date.month)} '{str(prev_end_date.year)[2:]}"

    balance_section = Row_template("l0", "Balance",
                            Row_template("l1", "Expected Balance",
            prev_bal :=         Row_template("l2", "Previous Balance", text2_format=prev_month_str),
               eb_cf :=         Row_template("l2", "Cash Flow"),
                            ),
                            Row_template("l1", "Current Balance",
                bank :=         Row_template("l2", "Bank", force=True),
                cash :=         Row_template("l2", "Cash"),
                                pad=5,
                            ),
                            pad=5,
                        )

    cash_flow_section.add_parent(eb_cf)
    prev_bal += prev_balance.total
    cash += final_balance.total
    bf.inc_text2_value(cur_month.tickets_claimed)

    other_revenue = defaultdict(int)   # {event: total}
    other_expenses = defaultdict(int)  # {event: total}
    for i in range(prev_index, final_index):  # loop from prev_index up to (but not including) final_index
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
        width, height = report.draw_init()
        page_width, page_height = report.pagesize
        width_copies = (page_width - 10) // (width + 10)
        height_copies = page_height // height
        print(f"{page_width=}, {width=}, {width_copies=}; {page_height=}, {height=}, {height_copies=}")
       #report.draw(2, 0)
       #report.draw(2 + width + 12, 0)
        for y_offset in range(0, round(page_height) - round(height), round(height) + 28):
            for x_offset in range(2, round(page_width) - 3 - round(width), round(width) + 22):
                report.draw(x_offset, y_offset)
        canvas_showPage()
        canvas_save()
    else:
        report.print_init()
        report.print()



if __name__ == "__main__":
    run()
