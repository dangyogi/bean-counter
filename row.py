# row.py

from decimal import Decimal, InvalidOperation
from datetime import date, datetime


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

    These have normal object attributes that can be set.  When the database is saved, these new value will be written to
    the database file.

    Default values are done with class attributes.  Any missing columns in an imported csv file are not set as attributes
    and default to the class attribute.

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
    def pkg_size(self):
        return Database.Products[self.item, self.supplier, self.supplier_id].pkg_size

    @property
    def pkg_weight(self):
        return Database.Products[self.item, self.supplier, self.supplier_id].pkg_weight

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

class Product_child(row):
    @property
    def supplier_used(self):
        if self.supplier is None or self.supplier_id is None:
            return Database.Items[self.item].supplier
        return self.supplier

    @property
    def supplier_id_used(self):
        if self.supplier is None or self.supplier_id is None:
            return Database.Items[self.item].supplier_id
        return self.supplier_id

class Inventory(Product_child):
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

class Orders(Product_child):
    # date=date_col(),
    # item=varchar(30),
    # qty=integer(),
    # supplier=varchar(50, null=True),
    # supplier_id=integer(null=True),
    # purchased_pkgs=integer(null=True),
    # purchased_units=integer(null=True),
    types = dict(
      # date=parse_date,
        item=str,
        qty=int,
        supplier=str,
        supplier_id=int,
        purchased_pkgs=int,
        purchased_units=int,
        location=str,
        price=Decimal,
    )

    in_database = False

    supplier = None
    supplier_id = None
    purchased_pkgs = None
    purchased_units = None
    location = None
    price = None
   #primary_keys = "date", "item"
   #required = frozenset(("date", "item", "qty"))
    required = frozenset(("item", "qty"))
    foreign_keys = "Items", "Products"

    @property
    def unit(self):
        return Database.Items[self.item].unit

    @property
    def pkg_size(self):
        return Database.Products[self.item, self.supplier_used, self.supplier_id_used].pkg_size

    @property
    def pkg_weight(self):
        return Database.Products[self.item, self.supplier_used, self.supplier_id_used].pkg_weight

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
    steps_completed = None
    primary_keys = "year", "month"
    required = frozenset(("month", "year"))

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

class Categories(row):
    # event=varchar(50),     # e.g., "meeting dinner", "breakfast"
    # category=varchar(50),  # e.g., "adv tickets", "door tickets", "50/50", "P.O. Reimbursement"
    # type=varchar(10),      # rev/exp
    # ticket_price=decimal(null=True),
    types = dict(
        event=str,
        category=str,
        type=str,
        ticket_price=Decimal,
    )

    ticket_price = None
    primary_keys = "event", "category"
    required = frozenset(("event", "category", "type"))

class Reconcile(row):
    # date=date_col(),
    # event=varchar(50),
    # category=varchar(50),
    # detail=varchar(50),
    # coin=decimal(default=0),
    # b1=integer(default=0),
    # b5=integer(default=0),
    # b10=integer(default=0),
    # b20=integer(default=0),
    # b50=integer(default=0),
    # b100=integer(default=0),
    # donations=decimal(default=0),
    types = dict(
        date=parse_date,
        event=str,
        category=str,
        detail=str,
        coin=Decimal,
        b1=int,
        b5=int,
        b10=int,
        b20=int,
        b50=int,
        b100=int,
        donations=Decimal,
    )

    coin = 0
    b1 = 0
    b5 = 0
    b10 = 0
    b20 = 0
    b50 = 0
    b100 = 0
    donations = 0
    required = frozenset(("date", "event", "category", "detail"))
    foreign_keys = "Categories",

    @property
    def total(self):
        return coin + b1 + 5*b5 + 10*b10 + 20*b20 + 50*b50 + 100*b100

    @property
    def type(self):
        return Database.Categories[self.event, self.category].type

    @property
    def ticket_price(self):
        return Database.Categories[self.event, self.category].ticket_price

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
        Categories, Reconcile,
       )


__all__ = "Decimal date set_database Rows".split()



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

