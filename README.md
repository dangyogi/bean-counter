# bean-counter
CLI bean counter app for local Men's Club.

Requires python reportlab library.

OVERVIEW

This uses .csv files (using '|' as the delimiter with no quoting) to store data.

The database is stored in one beans.csv file.  This file holds multiple tables.

Each table starts with the name of the table as a single column row. This is followed by a header row listing the attribute names (the
rows in python are class instances with attributes).  This second row is followed by the data rows, terminating in an empty row (no
columns).

There are several CLI python programs that each do one step.  Most of these are very simple.  Each one includes the following to get
access to the database:

from database import *

The program must call "load_database()" to load the beans.csv file into memory.  When it is done, it must also call "save_database()"
to write the memory contents back to beans.csv (replacing its prior contents).

The import above imports the following tables:

    - Items
    - Products
    - Inventory
    - Orders
    - Attendance
    - Categories
    - Reconcile

Each table is a python dict mapping the table keys to rows.  In addition they have a "load_csv()" method to load a csv file into
memory just for that one table.  This allows you to use your editor to edit reference tables and then load them into memory, from
which the "save_database()" will include them the beans.csv database.

Each table also has an "insert(attr=value...)" method to create new rows, and a "dump()" method (see code in table.py)
to dump the table to stdout.

I'm keeping my .csv files in this repo for backup.  If you find them somehow useful, feel free to use them.  Or just delete/ignore
them.
