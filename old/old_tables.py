# tables.py

from decimal import Decimal, InvalidOperation
from datetime import date, datetime
import os.path
import pickle 

from database import database


Database_filename = "beans.pcl"

def init_database():
    r'''Initializes to an empty database, discarding all previous data.

    Use `load` to load the database.
    '''
    return database()

def load(filename=Database_filename):
    r'''Loads database pickle from filename.
    '''
    with open(filename, 'rb') as f:
        return pickle.load(f)

def conditional_load(filename=Database_filename):
    if os.path.exists(filename):
        return load(filename)
    return init_database()


Database = conditional_load()


def parse_date(s):
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    return datetime.strptime(s, "%b %d, %y").date()

class row:
    r'''Also represents a table.
    '''
    primary_key = None
    primary_keys = None

    def __init__(self, **attrs):
        attrs_in = frozenset(name.lower() for name in attrs.keys())
        unknown_attrs = attrs_in.difference(self.types.keys())
        assert not unknown_attrs, f"{self.table}.__init__: unknown attrs={tuple(missing_attrs)}"
        missing_attrs = self.required.difference(attrs_in)
        assert not missing_attrs, f"{self.table}.__init__: missing attrs={tuple(missing_attrs)}, {attrs.keys()=}"
        for name, value in attrs.items():
            setattr(self, name.lower(), value)
        Database.add_row(self.table, self)

    @classmethod
    @property
    def table(cls):
        return cls.__name__

    @classmethod
    def from_csv(cls, header, row):
        return cls(**{name: cls.types[name.lower()](value.strip()) for name, value in zip(header, row) if value.strip() != ''})

    def key(self):
        if self.primary_key is not None:
            return getattr(self, self.primary_key)
        return tuple(getattr(self, key) for key in self.primary_keys)

    @classmethod
    def map(cls):
        return getattr(Database, cls.table)

    @classmethod
    def dump(cls):
        print(f"{cls.table}:")
        for row in cls.map().values():
            print("   ", end='')
            for i, attr in enumerate(cls.types.keys()):
                if i:
                    print(', ', end='')
                print(f"{attr}={getattr(row, attr)}", end='')
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
    # num_pkgs=double(),
    # supplier=varchar(50, null=True),
    # supplier_id=integer(null=True),
    types = dict(
        date=parse_date,
        item=str,
        num_pkgs=float,
        supplier=str,
        supplier_id=int,
    )

    supplier = None
    supplier_id = None
    primary_keys = "data item supplier supplier_id".split()
    required = frozenset(("date", "item", "num_pkgs"))
    foreign_keys = "Items", "Products"

class Orders(Product_child):
    # date=date_col(),
    # item=varchar(30),
    # qty=integer(),
    # supplier=varchar(50, null=True),
    # supplier_id=integer(null=True),
    types = dict(
        date=parse_date,
        item=str,
        qty=int,
        supplier=str,
        supplier_id=int,
    )

    supplier = None
    supplier_id = None
    primary_keys = "date", "item"
    required = frozenset(("date", "item", "qty"))
    foreign_keys = "Items", "Products"

class Attendance(row):
    # month=integer(),
    # year=integer(),
    # num_at_meeting=integer(null=True),
    # staff_at_breakfast=integer(null=True),
    # tickets_claimed=integer(null=True),
    types = dict(
        month=int,
        year=int,
        num_at_meeting=int,
        staff_at_breakfast=int,
        tickets_claimed=int,
    )

    num_at_meeting = None
    staff_at_breakfast = None
    tickets_claimed = None
    primary_keys = "year", "month"
    required = frozenset(("month", "year"))

    @property
    def meals_served(self):
        if self.staff_at_breakfast is None or self.tickets_claimed is None:
            return None
        return self.staff_at_breakfast + self.tickets_claimed

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
    # line_num=integer(),
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
        line_num=int,
        detail=str,
        coin=Decimal,
        b1=int,
        b5=int,
        b10=int,
        b20=int,
        b50=int,
        b100=int,
        nations=Decimal,
    )

    coin = 0
    b1 = 0
    b5 = 0
    b10 = 0
    b20 = 0
    b50 = 0
    b100 = 0
    donations = 0
    primary_keys = "date", "event", "category", "line_num"
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
Tables = (Items, Products,
          Inventory, Orders, Attendance,
          Categories, Reconcile,
         )

def find_table(name):
    for t in Tables:
        if t.table == name:
            return t
    raise AssertionError(f"find_table: table={name} not found")

def load_table(table, from_scratch=True):
    print("loading", table.table)
    Database.load_csv(table, f"{table.table}.csv", from_scratch=from_scratch)

def load_all(from_scratch=True):
    for table in Tables:
        if os.path.exists(f"{table.table}.csv"):
            load_table(table, from_scratch=from_scratch)
        else:
            print("load_all: skipping", table.table)

def purge_table(table):
    Database.purge(table)

def purge_all():
    for table in reversed(Tables):
        purge_table(table)

def one_time_init():
    global Database
    Database = init_database()

def save_database(filename=Database_filename):
    r'''Writes database pickle to filename.
    '''
    with open(filename, 'wb') as f:
        pickle.dump(Database, f)


__all__ = tuple("Decimal date Tables find_table load_table load_all purge_table purge_all one_time_init save_database".split()) \
        + tuple(t.table for t in Tables)

