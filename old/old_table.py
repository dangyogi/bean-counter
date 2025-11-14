# table.py

from string import Template
from collections import namedtuple
import atexit
import sqlite3


__all__ = "DB_conn transaction foreign_key table view column varchar date_col integer double decimal".split()


DB_conn = sqlite3.connect("beans.db")

print(f"{DB_conn.isolation_level=}")
print(f"{DB_conn.autocommit=}")

def namedtuple_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
   #print(f"namedtuple_factory: {cursor.description=}, {fields=}")
    cls = namedtuple("Row", fields)
    return cls._make(row)

DB_conn.row_factory = namedtuple_factory

atexit.register(DB_conn.close)

class transaction:
    r'''Automatically commits (no exceptions), or rollsback (for exceptions)
    '''
    def __enter__(self):
        # FIX: is BEGIN TRANSACTION required?
        return None  # nothing to bind to with variable

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            DB_conn.commit()
        else:
            DB_conn.rollback()
        return False  # do not suppress exceptions




def indent(template):
    t = template.lstrip('\n').rstrip()
    indent = len(t) - len(t.lstrip())
    return '\n'.join(line[indent:] for line in t.split('\n'))


class base_table:
    primary_key = None
    primary_keys = ()

    def __init__(self, name):
        self.name = name

    def execute(self, sql, values=None, rowcount=None):
        cur = DB_conn.cursor()
        if values is None:
            cur.execute(sql)
        else:
            cur.execute(sql, values)
        if rowcount is not None:
            assert cur.rowcount == rowcount, f"Got rowcount={cur.rowcount}, expected {rowcount}"
        cur.close()

    def create(self, drop=True, if_not_exists=False):
        if drop:
            self.drop(if_exists=True)
        self.execute(self.create_sql(if_not_exists))

    def drop(self, if_exists=True):
        self.execute(self.drop_sql(if_exists))

    def execute_get1(self, sql, values=None):
        r'''Asserts that only one row returned.

        Returns that row.
        '''
        cur = DB_conn.cursor()
        if values is None:
            cur.execute(sql)
        else:
            cur.execute(sql, values)
        assert cur.rowcount == 1, f"expected 1 row, got {cur.rowcount}"
        row = cur.fetchone()
        cur.close()
        return row

    def execute_get(self, sql, values=None):
        r'''Generates all rows.
        '''
        cur = DB_conn.cursor()
        if values is None:
            cur.execute(sql)
        else:
            cur.execute(sql, values)
        yield from cur.fetchall()
        cur.close()

    def where(self, where=None, key=None, keys=None):
        r'''Creates a sql WHERE clause.

        Only one of `key` and `keys` may be specified, not both.  If so, they are added to `where` matching the primary_key(s).

        The where is {col_name: exp}, which translates into "col_name = exp" clauses ANDed together.

        Returns WHERE clause, param values

        WHERE clause is preceeded by "\n " (indented one space on next line) to provide for absent WHERE clauses.  Thus the
        $where_clause in the sql template should be at the end of the line preceeding where it should appear (with no spaces).

        If all parameters are None, returns "", None

        Can be used with "SELECT", "UPDATE", or "DELETE" (which are all 6 chars long, so adding a space in front of "WHERE"
        right-aligns it with any of these).
        '''
        if key is not None:
            assert self.primary_key is not None, f"table({self.name}).where: got {key=}, but no primary_key in table"
            assert keys is None, f"table({self.name}).where: got both {key=} and {keys=}, only one allowed."
            if where is None:
                where = {}
            where[self.primary_key] = key
        elif keys is not None:
            assert self.primary_keys, f"table({self.name}).get1: got {keys=}, but no primary_keys on table"
            assert len(self.primary_keys) == len(keys), \
                   f"table({self.name}).get1: got {len(keys)} keys, with {len(self.primary_keys)} primary_keys on table"
            if where is None:
                where = {}
            where.update(dict(zip(self.primary_keys, keys)))
        if not where:
            return "", None
        conditions = []
        values = {}
        for name, value in where.items():
            conditions.append(f"{name} = :{name}")
            values[name] = value
        return f"\n WHERE {'\n   AND '.join(conditions)}", values

    def get1(self, key=None, keys=None):
        sql, values = self.get_sql(key=key, keys=keys)
        return self.execute_get1(sql, values)

    def get_sql(self, where=None, key=None, keys=None, join=None, more_sel=None):
        r'''where, key and keys go into the where clause.

        where is a dict of {col_name: exp}.  These translate into "col_name = exp" and are ANDed together.
        if key is not None, then primary_key: key is added to where.
        if keys is not None, the each primary_key[i]: keys[i] are added to where.

        If join is not None, it must be a table (or view).  An INNER JOIN to that table is added USING it's primary_key(s).

        Whether or not join is used, more_sel is dict of {added_col_name: exp}, which adds "exp AS added_col_name" clauses 
        to the end of the SELECT clause (which is otherwise just the columns from this table).

        Returns sql, param values.
        '''
        where_clause, values = self.where(where=where, key=key, keys=keys)
        sub_values = dict(name=self.name, where_clause=where_clause)
        if more_sel is not None:
            sub_values['sel'] = ''.join(f", {exp} AS {name}" for name, exp in more_sel.items())
        else:
            sub_values['sel'] = ''
        if join is not None:
            t = Template(indent("""
                    SELECT $name.*$sel
                      FROM $name
                           INNER JOIN $join USING ($keys)$where_clause;
                """))
            sub_values['join'] = join.name
            if join.primary_key is not None:
                sub_values['keys'] = join.primary_key
            else:
                sub_values['keys'] = ', '.join(join.primary_keys)
        else:
            t = Template(indent("""
                    SELECT *$sel
                      FROM $name$where_clause;
                """))
        return t.substitute(sub_values), values

    def get(self, **where):
        sql, values = self.get_sql(where)
        return self.execute_get(sql, values)


class foreign_key:
    def __init__(self, other_table, columns=None, on_delete=None, on_update=None):
        r'''Creates a foreign key contraint, either as a table constraint (with columns), or a column constraint (without).

        on_delete/on_update can be: NO ACTION, RESTRICT, SET NULL, SET DEFAULT or CASCADE
        '''
        self.other_table = other_table
        self.columns = columns
        self.on_delete = on_delete
        self.on_update = on_update

    def clause(self):
        tail = []
        if self.columns:
            tail.extend(["FOREIGN KEY", f"({', '.join(self.columns)})"])
        tail.extend(["REFERENCES", self.other_table])
        if self.on_delete is not None:
            tail.extend(["ON DELETE", self.on_delete.upper()])
        if self.on_update is not None:
            tail.extend(["ON UPDATE", self.on_update.upper()])
        return " ".join(tail)


class table(base_table):
    def __init__(self, table_name, primary_keys=(), foreign_keys=None, **columns):
        r'''primary_keys is a tuple of column names.

        foreign_keys is a instance of foreign_key (or None).
        '''
        super().__init__(table_name)
        self.columns = columns
        self.primary_keys = primary_keys
        self.foreign_keys = foreign_keys
        for name, col in columns.items():
            if col.primary_key:
                self.primary_key = name
                break

    def create_sql(self, if_not_exists=False):
        r'''Returns sql.
        '''
        t = Template(indent("""
                CREATE TABLE $if_not_exists$name (
                    $column_defs$table_constraints
                );
            """))
        table_constraints = []
        if self.primary_keys:
            table_constraints.append(f"PRIMARY KEY ({', '.join(self.primary_keys)})")
        if self.foreign_keys:
            table_constraints.append(self.foreign_keys.clause())
        return t.substitute(name=self.name, if_not_exists=("IF NOT EXISTS " if if_not_exists else ""),
                            column_defs=",\n    ".join(col.sql(name) for name, col in self.columns.items()),
                            table_constraints="".join(f",\n    {clause}" for clause in table_constraints))

    def drop_sql(self, if_exists=True):
        r'''Returns sql.
        '''
        if if_exists:
            return f"DROP TABLE IF EXISTS {self.name};"
        return f"DROP TABLE {self.name};"

    def delete1(self, key):
        sql, values = self.delete_sql({self.primary_key: key})
        self.execute(sql, values, rowcount=1)

    def insert(self, or_clause=None, **values):
        r'''or_clause may be: ABORT, FAIL, IGNORE, REPLACE or ROLLBACK (converted to uppercase)
        '''
        sql, values = self.insert_sql(values, or_clause=or_clause)
        self.execute(sql, values)

    def insert_sql(self, values, or_clause=None):
        r'''or_clause may be: ABORT, FAIL, IGNORE, REPLACE or ROLLBACK (converted to uppercase)

        Returns sql, param values.
        '''
        t = Template(indent("""
                INSERT$or_clause INTO $name($columns)
                VALUES ($params);
            """))
        return (t.substitute(or_clause=(f" OR {or_clause.upper()}" if or_clause is not None else ""), name=self.name,
                             columns=', '.join(values.keys()), params=', '.join(f":{name}" for name in values.keys())),
                values)

    def update(self, where=None, key=None, keys=None, **values):
        sql, values = self.update_sql(values, where=where, key=key, keys=keys)
        self.execute(sql, values)

    def update_sql(self, values, where=None, key=None, keys=None):
        r'''Returns sql, param values.
        '''
        where_clause, values = self.where(where=where, key=key, keys=keys)
        if values is None:
            values = {}
        sets = []
        for name, value in values.items():
            sets.append(f"{name} = :{name}_value")
            values[f"{name}_value"] = value
        t = Template(indent("""
                UPDATE $name
                   SET $sets$where;
            """))
        return t.substitute(name=self.name, sets=',\n       '.join(sets), where=where_clause), values

    def delete(self, key=None, keys=None, **where):
        sql, values = self.delete_sql(where=where, key=key, keys=keys)
        self.execute(sql, values)
    
    def delete_sql(self, where=None, key=None, keys=None):
        r'''Returns sql, param values.
        '''
        where_clause, values = self.where(where=where, key=key, keys=keys)
        t = Template(indent("""
                DELETE FROM $name$where_clause;
            """))
        return t.substitute(name=self.name, where_clause=where_clause), values


class view(base_table):
    def __init__(self, view_name, table, join=None, **extra_cols):
        super().__init__(view_name)
        self.table = table
        self.primary_key = self.table.primary_key
        self.primary_keys = self.table.primary_keys
        self.join = join
        self.extra_cols = extra_cols

    def create_sql(self, if_not_exists=False):
        r'''Returns sql.
        '''
        sub_values = dict(name=self.name,
                          if_not_exists=("IF NOT EXISTS " if if_not_exists else ""),
                          table_name=self.table.name,
                          extra_cols=", ".join(f"{expr} AS {name}" for name, expr in self.extra_cols.items()))
        if self.join is not None:
            t = Template(indent("""
                    CREATE VIEW $if_not_exists$name
                        AS SELECT $table_name.*, $extra_cols
                             FROM $table_name
                                  INNER JOIN $join USING ($keys);
                """))
            sub_values['join'] = self.join.name
            if self.join.primary_key is not None:
                sub_values['keys'] = self.join.primary_key
            else:
                sub_values['keys'] = ', '.join(self.join.primary_keys)
        else:
            t = Template(indent("""
                    CREATE VIEW $if_not_exists$name
                        AS SELECT *, $extra_cols
                             FROM $table_name;
                """))
        return t.substitute(sub_values)

    def drop_sql(self, if_exists=True):
        r'''Returns sql.
        '''
        if if_exists:
            return f"DROP VIEW IF EXISTS {self.name};"
        return f"DROP VIEW {self.name};"


class column:
    def __init__(self, type, primary_key=False, null=False, unique=False, default=None, collate=None, references=None):
        r'''collate can be: BINARY, NOCASE or RTRIM

        references is an instance of foreign_key.
        '''
        self.type = type
        self.primary_key = primary_key
        self.null = null
        self.unique = unique
        self.default = default
        self.collate = collate
        self.references = references

    def sql(self, name):
        t = Template("$name $type$rest")
        return t.substitute(name=name, type=self.type, rest=''.join(f" {clause}" for clause in self.sql_rest()))

    def sql_rest(self):
        if self.primary_key:
            yield "PRIMARY KEY"
        if not self.null:
            yield "NOT NULL"
        if self.unique:
            yield "UNIQUE"
        if self.default is not None:
            if isinstance(self.default, str):
                yield f"DEFAULT '{self.default}'"
            else:
                yield f"DEFAULT {self.default}"
        if self.collate is not None:
            yield f"COLLATE {self.collate.upper()}"
        if self.references is not None:
            yield self.references.clause()

class varchar(column):
    def __init__(self, max_len=None, **args):
        if max_len is None:
            super().__init__("VARCHAR", **args)
        else:
            super().__init__(f"VARCHAR({max_len})", **args)

class date_col(column):
    def __init__(self, **args):
        super().__init__("DATE", **args)

class integer(column):
    def __init__(self, **args):
        super().__init__("INTEGER", **args)

class double(column):
    def __init__(self, **args):
        super().__init__("DOUBLE PRECISION", **args)

class decimal(column):
    def __init__(self, max_digits=9, decimals=2, **args):
        super().__init__(f"DECIMAL({max_digits}, {decimals})", **args)


# CREATE [UNIQUE] INDEX [IF NOT EXISTS] <index_name> ON
#   <table_name> (<column> [COLLATE <collation_name>] [ASC|DESC], ...) [WHERE <expr>]
#
# DROP INDEX [IF EXISTS] <index_name>

# CREATE VIEW [IF NOT EXISTS] <view_name> [( <column_name>, ... )] AS <select>
#
# DROP VIEW [IF EXISTS] <view_name>



if __name__ == "__main__":
    t1 = table("foobar", primary_keys=("name", "date"), name=varchar(30), date=date_col(), price=decimal(null=True))
    t2 = table("bogus", name=varchar(30, primary_key=True, default="omitted"), date=date_col(), price=decimal(null=True))
   #print("sqlite3.paramstyle", sqlite3.paramstyle)
    print("t1.create_sql():")
    print(t1.create_sql())
    print("t2.create_sql():")
    print(t2.create_sql())
    print("t1.create_sql(if_not_exists=True):")
    print(t1.create_sql(if_not_exists=True))
    print("t1.get_sql()")
    sql, values = t1.get_sql()
    print(sql)
    print(values)
    print("t1.get_sql({'col1': 24})")
    sql, values = t1.get_sql({'col1': 24})
    print(sql)
    print(values)
    print("t1.get_sql({'col1': 24, 'col2': 'some string'})")
    sql, values = t1.get_sql({'col1': 24, 'col2': 'some string'})
    print(sql)
    print(values)
    print("t2.get_sql(key='Otis')")
    sql, values = t2.get_sql(key='Otis')
    print(sql)
    print(values)
    print("t1.get_sql(keys=('Otis', 24))")
    sql, values = t1.get_sql(keys=('Otis', 24))
    print(sql)
    print(values)
