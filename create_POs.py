# create_POs.py

from datetime import date, timedelta
from collections import defaultdict
from operator import itemgetter
from itertools import groupby
import csv

from database import *
from report import *


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--month", "-m", type=int, default=date.today().month)
    parser.add_argument("--po-num-index", "-i", type=int, default=1)
    parser.add_argument("--pdf", "-p", action="store_true", default=False)

    args = parser.parse_args()

    load_database()

    today = date.today()

    year = today.year
    month = args.month
    if today.month < month:
        year -= 1

    cur_month = Months[year, month]
    bf_date = cur_month.breakfast_date
    po_num = f"{str(bf_date.year)[2:]}{bf_date.month:02}{args.po_num_index}"

    with open("Orders.csv", "r") as f:
        csv_reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        table_name = next(csv_reader)
        assert table_name == ["Orders"], f'Expected table_name="Orders", got {table_name}'
        headers = [hdr.strip() for hdr in next(csv_reader)]
        
        def read_rows():
            for row in csv_reader:
                assert len(headers) == len(row), f"read_rows: {len(headers)=} != {len(row)=}"
                row_attrs = {}
                for name, value in zip(headers, row):
                    value = value.strip()
                    if value == '':
                        value = None
                    elif name in ('qty', 'supplier_id'):
                        value = int(value)
                    row_attrs[name] = value
                if row_attrs["supplier"] is None and row_attrs["supplier_id"] is None:
                    item = Items[row_attrs["item"]]
                    row_attrs["supplier"] = item.supplier
                    row_attrs["supplier_id"] = item.supplier_id
                row_attrs["product"] = Products[row_attrs["item"], row_attrs["supplier"], row_attrs["supplier_id"]]
               #print(f"read_rows: item={value=}, {item.supplier=}")
                yield row_attrs

        set_canvas("Purchase-Orders-" + str(po_num), landscape=True)
        reports = {}  # {supplier: report}
        grand_total = 0
        for supplier, items in groupby(sorted(read_rows(), key=itemgetter("supplier", "item")),
                                       key=itemgetter("supplier")):
           #print(f"in for: {supplier=}")
            report, total = gen_PO(supplier, items, po_num, bf_date)
            if total:
                reports[supplier] = report
                grand_total += total

    total_report = gen_Total_POs(grand_total, po_num, bf_date)

    if args.pdf:
        top_margin = 15
        total_gap = 30
        gap = 15  # between reports in points
        left_margin = 2
        max_width = 0
        total_width, height = total_report.draw_init()
        y_offset = top_margin + height + total_gap
        widths = {}
        y_offsets = {}
        for supplier in "Sams Walmart Gordon Amazon".split():
            if supplier in reports:
                report = reports[supplier]
                y_offsets[supplier] = y_offset
                width, height = report.draw_init()
                widths[supplier] = width
                if width > max_width:
                    max_width = width
                y_offset += height + gap

        page_width = get_pagesize()[0]

        total_report.draw(x_offset=(page_width - total_width) // 2 + left_margin,
                          y_offset=top_margin)
        for supplier in "Sams Walmart Gordon Amazon".split():
            if supplier in reports:
                report = reports[supplier]
                report.draw(x_offset=(page_width - widths[supplier]) // 2 + left_margin,
                            y_offset=y_offsets[supplier])

        canvas_showPage()
        canvas_save()
    else:
        total_report.print_init()
        total_report.print()
        for supplier in "Sams Walmart Gordon Amazon".split():
            if supplier in reports:
                report = reports[supplier]
                report.print_init()
                print()
                report.print()

def gen_PO(supplier, items, po_num, bf_date):
    r'''Returns report, total
    '''
    # generate POs Report
   #print(f"gen_PO({supplier=}, {po_num=}, {bf_date:%b %d, %y}")
    report = Report(# 7 columns
                    title=(Centered(span=7, size="title", bold=True),),
                    header1=(Left(bold=True, span=2), Left(skip=4)),
                    header2=(Right(bold=True), Right(bold=True), Left(bold=True),
                             Right(bold=True), Left(bold=True), Right(bold=True), Right(bold=True)),
                    body=(Right(), Right(), Left(), Right(), Left(), Right(), Right()),
                    total=(Right(bold=True, span=6), Right()),
                   )

    po_num_supplier = po_num + supplier[0].upper()
    report.new_row("title", supplier + " Purchase Order")
    report.new_row("header1", "Date", bf_date.strftime("%b %d, %y"), pad=10)
    report.new_row("header1", "P.O. Num", po_num_supplier)
    report.new_row("header2", "Line", "Qty", "Item", "Item #", "Location", "Est Price ea", "Ext Price", pad=6)

    total = 0
    for line, item in enumerate(items, 1):
       #print(f"gen_PO: {item=}")
        qty = item["qty"]
        product = item["product"]
        price = product.price
        ext_price = qty * price
        total += ext_price
        report.new_row("body", line, qty, product.name, product.item_num, product.location,
                       price, ext_price)
    report.new_row("total", "Total", total, pad=10)
    return report, total

def gen_Total_POs(grand_total, po_num, bf_date):
    r'''Returns report
    '''
    # generate POs Report
    report = Report(# 2 columns
                    title=(Centered(span=2, bold=True, size="title"),),
                    row=(Left(bold=True), Right()),
                   )
    report.new_row("title", "Purchase Orders")
    report.new_row("row", "Date", bf_date.strftime("%b %d, %y"), pad=5)
    row = report.new_row("row", "P.O. Num Base")
    row.set_text2("(Year Mth Seq#)")
    row.next_cell(po_num)
    report.new_row("row", "Total", grand_total)
    report.new_row("row", "Approval")
    return report




if __name__ == "__main__":
    run()
