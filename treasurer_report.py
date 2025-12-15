# treasurer_report.py

from datetime import date, timedelta
from collections import defaultdict
from itertools import groupby
from operator import attrgetter

from database import *
from report import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--month", "-m", type=int, default=date.today().month)
    parser.add_argument("--year", "-y", type=int, default=date.today().year)
    parser.add_argument("--pdf", "-p", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    today = date.today()

    year = args.year
    if year < 2000:
        year += 2000
    month = args.month
    if today.month < month:
        year -= 1

    print()
    print("Current month", abbr_month(month), year)
    print()
    cur_month = Months[year, month]
    end_date = cur_month.end_date

    def find_final(end_date):
        r'''Find the final balance in the Reconcile table for end_date.

        Returns index, recon row.
        '''
        start_index = Reconcile.first_date(end_date)   # start_index into Reconcile for end_date
       #print(f"{end_date=}, {start_index=}")
        error_msg = f"{end_date.strftime('%b %d, %y')}, monthly, final balance not found in Reconcile"
        for i in range(start_index, len(Reconcile)):  # loop from start_index to the end of Reconcile
            recon = Reconcile[i]
            assert recon.date == end_date, error_msg
            if recon.account == 'cash' and recon.detail == 'w/starts':
               #print("found final balance")
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

    prev_end_date  = cur_month.start_date - timedelta(days=1)
    prev_index, prev_balance = find_final(prev_end_date)

    prev_month_str = f"{abbr_month(prev_end_date.month)} '{str(prev_end_date.year)[2:]}"

    # Create Row_templates from Accounts:
    accounts = {}
    sections = []
    picks = {}  # expense, revenue, bf, cash flow, balance, bank, cash
    for section, categories in groupby(Accounts.values(), key=attrgetter("section")):
        # "Cash Flow" and "Balance"
        if section is None:
            continue
        cats = []
        if section == "Balance":
            cat_kws = dict(force=True)
            cats.append(Row_template("l1", "Expected Balance", 
        prev_bal :=         Row_template("l2", "Previous Balance", text2_format=prev_month_str),
           eb_cf :=         Row_template("l2", "Cash Flow"),
                        ))
        else:
            cat_kws = dict()
        for category, types in groupby(categories, key=attrgetter("category")):
            # "Breakfast", "Other", "Current Balance"
            if section == "Balance":
                type_kws = dict(force=True)
            else:
                type_kws = dict()
            types_ = []
            for type, account_rows in groupby(types, key=attrgetter("type")):
                accounts_ = []
                if section != "Balance":
                    for account_row in account_rows:
                        account = account_row.account
                        if account not in ("revenue", "expense"):
                            if account.endswith(" tickets"):
                                templ = Row_template("l3", account, text2_format="({})")
                            else:
                                templ = Row_template("l3", account)
                            accounts[account] = templ
                            accounts_.append(templ)
                if type == "Expenses":
                    templ = Row_template("l2", type, *accounts_, invert_parent=True, **type_kws)
                    if category == "Other":
                        picks["expense"] = templ
                else:
                    templ = Row_template("l2", type, *accounts_, **type_kws)
                    if category == "Other":
                        picks["revenue"] = templ
                if section == "Balance":
                    picks[type.lower()] = templ
                types_.append(templ)
                type_kws['pad'] = 5
            if category == "Breakfast":
                templ = Row_template("l1", category, *types_, text2_format="({}) showed up", **cat_kws)
                picks["bf"] = templ
            else:
                templ = Row_template("l1", category, *types_, **cat_kws)
            cats.append(templ)
            cat_kws['pad'] = 5
        if section == "Balance":
            templ = Row_template("l0", section, *cats, hide_value=True, pad=5)
        else:
            templ = Row_template("l0", section, *cats, pad=5)
        sections.append(templ)
        picks[section.lower()] = templ

    picks["cash flow"].add_parent(eb_cf)
    prev_bal += prev_balance.total
    picks["cash"] += final_balance.total
    picks["bf"].inc_text2_value(cur_month.tickets_claimed)

    other_revenue = defaultdict(int)   # {account: total}
    other_expenses = defaultdict(int)  # {account: total}

    rev_details = {}
    exp_details = {}
    for i in range(prev_index, final_index):  # loop from prev_index up to (but not including) final_index
        recon = Reconcile[i]
        if recon.account == "revenue":
            if recon.detail not in rev_details:
                templ = Row_template("l3", recon.detail)
                rev_details[recon.detail] = templ
                picks["revenue"].add_child(templ)
            rev_details[recon.detail] += recon.total
            accounts["donations"] += recon.donations
        elif recon.account == "expense":
            if recon.detail not in exp_details:
                templ = Row_template("l3", recon.detail)
                exp_details[recon.detail] = templ
                picks["expense"].add_child(templ)
            exp_details[recon.detail] += recon.total
            accounts["donations"] += recon.donations
        elif recon.section == "Cash Flow":
            if recon.account.endswith(" tickets"):
                accounts[recon.account].inc_text2_value(recon.tickets_sold)
            accounts[recon.account] += recon.total
            if (recon.account, "start") in Starts:
                accounts[recon.account] -= Starts[recon.account, "start"].total
            if recon.category == "Breakfast":
                accounts["bf donations"] += recon.donations
            else:
                accounts["donations"] += recon.donations

    picks["cash flow"].insert(report)
    picks["balance"].insert(report)

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
