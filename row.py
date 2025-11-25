# row.py

from decimal import Decimal, InvalidOperation
from datetime import date, datetime
import math


TUESDAY  = 1
SATURDAY = 5


def set_database(database):
    global Database
    Database = database

def parse_date(s):
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    return datetime.strptime(s, "%b %d, %y").date()

def parse_set(s):
    return set(x.strip() for x in s.split(','))

class row:
    r'''One row in a database table.

    These have normal object attributes that can be set.  When the database is saved, these new values will
    be written to the database file.

    Default values are done with class attributes.  Any missing columns in an imported csv file are not set as
    attributes and default to the class attribute.

    Additional non-stored attributes (similar to relational view) are simply done with a standard python @property.
    '''
    primary_key = None
    primary_keys = None
    in_database = True

    def __init__(self, **attrs):
        attrs_in = frozenset(name.lower() for name in attrs.keys())
        unknown_attrs = attrs_in.difference(self.types.keys())
        assert not unknown_attrs, f"{self.table_name}.__init__: unknown attrs={tuple(missing_attrs)}"
        missing_attrs = self.required.difference(attrs_in)
        assert not missing_attrs, f"{self.table_name}.__init__: missing attrs={tuple(missing_attrs)}, {attrs.keys()=}"
        for name, value in attrs.items():
            setattr(self, name.lower(), value)

    @classmethod
    @property
    def table_name(cls):
        return cls.__name__

    @classmethod
    def from_csv(cls, header, row, ignore_unknown_cols=False):
        r'''strips both the names in header and the values in row.

        names in header are converted to lowercase as key for cls.types.

        attrs with an empty value are not loaded, so that they have their default values.
        '''
        attrs = {}
        assert len(header) == len(row), f"{cls.table_name}.from_csv: len(header)={len(header)} != len(row)={len(row)}"
        for name, value in zip(header, row):
            name = name.strip().lower()
            value = value.strip()
            if name not in cls.types:
                if not ignore_unknown_cols:
                    raise AssertionError(f"{cls.table_name}.from_csv: unknown attr={name}")
            elif value != '':
                attrs[name] = cls.types[name](value)
        return cls(**attrs)

    def csv_value(self, name):
        value = getattr(self, name)
        if value is None:
            return ''
        if isinstance(value, date):
            return value.strftime("%b %d, %y")
        if isinstance(value, set):
            return ','.join(sorted(value))
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value)

    def key(self):
        if self.primary_key is not None:
            return getattr(self, self.primary_key)
        return tuple(getattr(self, key) for key in self.primary_keys)

    def dump(self):
        r'''Appends atttr values onto end of current print line.

        Ends with newline.
        '''
        for i, attr in enumerate(self.types.keys()):
            if i:
                print(', ', end='')
            print(f"{attr}={getattr(self, attr)}", end='')
        print()


class Items(row):
    # item=varchar(30, primary_key=True),
    # unit=varchar(30),
    # supplier=varchar(50, null=True),
    # supplier_id=integer(null=True),
    # num_per_meal=double(null=True),
    # num_per_table=double(null=True),
    # num_per_serving=double(null=True))
    types = dict(
        item=str,
        unit=str,
        supplier=str,
        supplier_id=int,
        num_per_meal=float,
        num_per_table=float,
        num_per_serving=float,
    )

    supplier = None
    supplier_id = None
    num_per_meal = None
    num_per_table = None
    num_per_serving = None
    primary_key = 'item'
    required = frozenset(("item", "unit"))
    foreign_keys = "Products",

    @property
    def product(self):
        return Database.Products[self.item, self.supplier, self.supplier_id]

    @property
    def pkg_size(self):
        return self.product.pkg_size

    @property
    def pkg_weight(self):
        return self.product.pkg_weight

class Products(row):
    # item=varchar(30, references=foreign_key("Items", on_delete="cascade", on_update="cascade")),
    # supplier=varchar(50),
    # supplier_id=integer(default=1),
    # name=varchar(100),
    # item_num=varchar(50, null=True),
    # location=varchar(50, null=True),
    # price=decimal(),
    # pkg_size=integer(null=True),
    # pkg_weight=double(null=True),
    # note=varchar(200, null=True),
    types = dict(
        item=str,
        supplier=str,
        supplier_id=int,
        name=str,
        item_num=str,
        location=str,
        price=Decimal,
        pkg_size=int,
        pkg_weight=float,
        note=str,
    )

    supplier_id = 1
    item_num = None
    location = None
    pkg_size = None
    pkg_weight = None
    note = None
    primary_keys = "item", "supplier", "supplier_id"
    required = frozenset(("item", "supplier", "name", "price"))
    foreign_keys = "Items",

    @property
    def unit(self):
        return Database.Items[self.item].unit

    @property
    def price_per_unit(self):
        if self.pkg_size is None:
            return None
        return self.price / self.pkg_size

    @property
    def oz_per_unit(self):
        if self.pkg_weight is None or self.pkg_size is None:
            return None
        return self.pkg_weight / self.pkg_size

class Inventory(row):
    # date=date_col(),
    # item=varchar(30),
    # code=varchar(20),
    #   - count
    #   - purchased (exact count)
    #   - used (exact count)
    #   - consumed (estimate)
    #   - estimate (includes uncertainty)
    # num_pkgs=double(null=True),
    # num_units=integer(null=True),
    # uncertainty=integer(null=True),
    types = dict(
        date=parse_date,
        item=str,
        code=str,
        num_pkgs=float,
        num_units=int,
        uncertainty=int,
    )

    num_pkgs = 0
    num_units = 0
    uncertainty = 0
    primary_keys = "date item code".split()
    required = frozenset(("date", "item", "code"))
    foreign_keys = "Items",

class Orders(row):
    # item=varchar(30),
    # qty=integer(null=True),             # None if no P.O. was created, and purchased_units used.
    # supplier=varchar(50, null=True),
    # supplier_id=integer(null=True),
    # purchased_pkgs=integer(null=True),
    # purchased_units=integer(null=True),
    # location=varchar(20, null=True),
    # price=Decimal(null=True),
    types = dict(
        item=str,
        qty=int,
        supplier=str,
        supplier_id=int,
        purchased_pkgs=int,   # if None, defaults to qty
        purchased_units=int,  # added to purchased_pkgs
        location=str,         # updates Products if not None
        price=Decimal,        # updates Products if not None
    )

    in_database = False

    qty = None
    supplier = None
    supplier_id = None
    purchased_pkgs = None
    purchased_units = None
    location = None
    price = None
   #primary_keys = "date", "item"
    required = frozenset(("item",))
    foreign_keys = "Items", "Products"

    @property
    def item_row(self):
        return Database.Items[self.item]

    @property
    def product(self):
        if self.supplier is None or self.supplier_id is None:
            return self.item_row.product
        return Database.Products[self.item, self.supplier, self.supplier_id]

    @property
    def unit(self):
        return self.item_row.unit

    @property
    def pkg_size(self):
        return self.product.pkg_size

    @property
    def pkg_weight(self):
        return self.product.pkg_weight

Months_abbreviated = (None,
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
)

class Months(row):
    # month=integer(),
    # year=integer(),
    # min_order=integer(null=True),
    # max_perishable=integer(null=True),
    # max_non_perishable=integer(null=True),
    # num_at_meeting=integer(null=True),
    # staff_at_breakfast=integer(null=True),
    # tickets_claimed=integer(null=True),
    # start_date=date(null=True),
    # end_date=date(null=True),
    # end_bank_bal=Decimal(null=True),
    # end_cash_bal=Decimal(null=True),
    # steps_completed=set(null=True),
    types = dict(
        month=int,
        year=int,
        min_order=int,
        max_perishable=int,
        max_non_perishable=int,
        num_at_meeting=int,
        staff_at_breakfast=int,
        tickets_claimed=int,
        start_date=parse_date,
        end_date=parse_date,
        end_bank_bal=Decimal,
        end_cash_bal=Decimal,
        steps_completed=parse_set,
    )

    min_order = None
    max_perishable = None
    max_non_perishable = None
    num_at_meeting = None
    staff_at_breakfast = None
    tickets_claimed = None
    start_date = None
    end_date = None
    end_bank_bal = None
    end_cash_bal = None
    steps_completed = None
    primary_keys = "year", "month"
    required = frozenset(("month", "year"))

    @property
    def month_str(self):
        return f"{Months_abbreviated[self.month]}, {str(self.year)[2:]}"

    @property
    def meals_served(self):
        if self.staff_at_breakfast is None or self.tickets_claimed is None:
            return None
        return self.staff_at_breakfast + self.tickets_claimed

    @property
    def meeting_date(self):
        return self.nth_day(1, TUESDAY)

    @property
    def breakfast_date(self):
        return self.nth_day(2, SATURDAY)

    def nth_day(self, n, day):
        firstday = date(self.year, self.month, 1).weekday()
        days_to_day = day - firstday
        if days_to_day >= 0:
            return date(self.year, self.month, days_to_day + 1 + 7 * (n - 1))
        return date(self.year, self.month, days_to_day + 8 + 7 * (n - 1))

class Globals(row):
    # name=varchar(50),                # e.g., "meeting dinner", "breakfast"
    # int=Decimal(null=True)
    # decimal=Decimal(null=True)
    types = dict(
        name=str,
        int=int,
        decimal=Decimal,
    )

    int = None
    decimal = None
    primary_key = "name"
    required = frozenset(("name",))

class Categories(row):
    # event=varchar(50),                # e.g., "meeting dinner", "breakfast"
    # category=varchar(50),             # e.g., "adv tickets", "door tickets", "50/50", "P.O. Reimbursement"
    # type=varchar(10, null=True),      # rev/exp
    types = dict(
        event=str,
        category=str,
        type=str,
    )

    type = None
    primary_keys = "event", "category"
    required = frozenset(("event", "category"))

class bills:
    types = dict(
        coin=Decimal,
        b1=int,
        b5=int,
        b10=int,
        b20=int,
        b50=int,
        b100=int,
    )
    coin = 0
    b1 = 0
    b5 = 0
    b10 = 0
    b20 = 0
    b50 = 0
    b100 = 0

    def __init__(self, coin=0, b1=0, b5=0, b10=0, b20=0, b50=0, b100=0):
        self.coin = coin
        self.b1 = b1
        self.b5 = b5
        self.b10 = b10
        self.b20 = b20
        self.b50 = b50
        self.b100 = b100

    @classmethod
    def value(cls, attr):
        r'''The monetary value of `attr`.
        '''
        if attr == 'coin':
            return 1
        assert attr[0] == 'b', f"expected attr starting with 'b', got {attr=}"
        return int(attr[1:])

    def copy(self):
        return bills(**self.as_attrs())

    def as_attrs(self):
        return {key: getattr(self, key) for key in bills.types.keys()}

    def __add__(self, bill2):
        r'''Returns new bills object.
        '''
        return bills(**{key: getattr(self, key) + getattr(bill2, key) for key in bills.types.keys()})

    def __sub__(self, bill2):
        r'''Returns new bills object.
        '''
        return bills(**{key: getattr(self, key) - getattr(bill2, key) for key in bills.types.keys()})

    def __iadd__(self, bill2):
        r'''Adds bill2 to self.
        '''
        for key in bills.types.keys():
            self.add_to_attr(key, bill2)
        return self

    def __isub__(self, bill2):
        r'''Subtracts bill2 from self.
        '''
        for key in bills.types.keys():
            self.sub_from_attr(key, bill2)
        return self

    def add_to_attr(self, attr, inc):
        r'''If inc is bills, gets attr from inc; else inc must be the number to add.
        '''
        if isinstance(inc, bills):
            inc = getattr(inc, attr)
        setattr(self, attr, getattr(self, attr) + inc)

    def sub_from_attr(self, attr, dec):
        r'''If dec is bills, gets attr from dec; else dec must be the number to subtract.
        '''
        if isinstance(dec, bills):
            dec = getattr(dec, attr)
        setattr(self, attr, getattr(self, attr) - dec)

    @property
    def total(self):
        return sum(self.value(key) * getattr(self, key) for key in bills.types.keys())

    def print(self, file):
        r'''Appends bill columns to end of current print line.

        Terminates the line.
        '''
        print(f"|{self.coin:5.02f}", end='', file=file)
        print(f"|{self.b1:3d}", end='', file=file)
        print(f"|{self.b5:3d}", end='', file=file)
        print(f"|{self.b10:3d}", end='', file=file)
        print(f"|{self.b20:3d}", end='', file=file)
        print(f"|{self.b50:3d}", end='', file=file)
        print(f"|{self.b100:4d}", end='', file=file)
        print(f"|{self.total:8.02f}", file=file)

class Starts(row, bills):  # row first, so it's __init__ is used.
    # event=varchar(50),
    # category=varchar(50),
    # detail=varchar(50, null=True),
    # ... bills
    types = dict(
        event=str,
        category=str,
        detail=str,
    )
    types.update(bills.types)
    detail = None
    required = frozenset(("event", "category", "detail"))
    primary_keys = "event", "category", "detail"
    foreign_keys = "Categories",

    @property
    def type(self):
        return Database.Categories[self.event, self.category].type

class Reconcile(Starts):
    # date=date_col(),
    # ... Starts
    # donations=decimal(null=True),
    types = dict(
        date=parse_date,
    )
    types.update(Starts.types)
    types["donations"]=Decimal

    donations = 0
    required = frozenset(("date", "event", "category"))
    primary_keys = None

    @property
    def total(self):
        return super().total() - self.donations

    @property
    def ticket_price(self):
        if self.event == "breakfast" and self.category.endswith(" tickets"):
            return Database.Globals[self.category[-1] + " price"].int
        return None

    @property
    def tickets_sold(self):
        price = self.ticket_price
        if price is None:
            return None
        return int(math.ceil(self.total / price))

def convert(s):
    s = s.strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%b %d, %y").date()
    except ValueError:
        pass
    i = s.find('.')
    if i >= 0 and i + 3 == len(s):
        # Has 2 chars after the '.'
        try:
            return Decimal(s)
        except InvalidOperation:
            pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


# These must be in logical order based on what has to be defined first
Rows = (Items, Products,
        Inventory, Orders, Months,
        Globals, Categories, Starts, Reconcile,
       )


__all__ = "Decimal date set_database bills Rows".split()



if __name__ == "__main__":
    with open("database.py", 'w') as f:
        print(
"""# database.py

# Do not edit!  This is machine generated by running "python row.py".

from table import *

""", file=f)
        for t in Rows:
            print(f"{t.table_name} = Tables['{t.table_name}']", file=f)
            print(file=f)

