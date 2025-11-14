# command.py

import tables



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--init", "-i", action="store_true", default=False)
    parser.add_argument("--tables", "-t", action="store_true", default=False)
    parser.add_argument("--purge", "-p", default=None)
    parser.add_argument("--load", "-l", default=None)
    parser.add_argument("--dump", "-d", default=None)
    parser.add_argument("--purge-all", "-P", action="store_true", default=False)
    parser.add_argument("--load-all", "-L", action="store_true", default=False)

    args = parser.parse_args()

    if args.tables:
        print("Tables:")
        for t in tables.Tables:
            print('  ', t.table)

    if args.init:
        tables.one_time_init()
    if args.purge_all:
        print("running purge_all")
        tables.purge_all()
    elif args.purge is not None:
        print("running purge", args.purge)
        tables.purge_table(tables.find_table(args.purge))

    if args.load_all:
        print("running create_all")
        tables.load_all()
    elif args.load is not None:
        print("running load", args.load)
        tables.load_table(tables.find_table(args.load))

    if args.dump is not None:
        tables.find_table(args.dump).dump()

    tables.save_database()
