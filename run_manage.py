"""
Script with utils managing the SQL database:
    - dump/restore/vacuum database
    - reset/create database
    - manage studies
    - show statistics

The options are specified with command line arguments.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import sys
import argparse
from config import data_common
from pyfreecoil import manage


if __name__ == "__main__":
    # get the main parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q", "--quiet",
        action="store_true", dest="quiet",
        help="execute command without prompt",
    )
    subparsers = parser.add_subparsers(required=False, dest="command")

    # basic database utils
    subparsers.add_parser("stat", help="display database statistics")
    subparsers.add_parser("reset", help="initialize the database (delete previous content)")
    subparsers.add_parser("vacuum", help="vacuum the database (delete unused content)")

    # dump/restore utils
    parser_tmp = subparsers.add_parser("dump", help="dump the content of the database")
    parser_tmp.add_argument("filename", type=str, help="name/path of the dump file")
    parser_tmp = subparsers.add_parser("restore", help="restore the content of the database")
    parser_tmp.add_argument("filename", type=str, help="name/path of the dump file")

    # database study utils
    parser_tmp = subparsers.add_parser("delete", help="delete a study (including the associated designs)")
    parser_tmp.add_argument("name", type=str, help="name of the study to be deleted")
    parser_tmp = subparsers.add_parser("create", help="create a study (without designs)")
    parser_tmp.add_argument("name", type=str, help="name of the study to be created")
    parser_tmp = subparsers.add_parser("rename", help="rename a study (keep the associated designs)")
    parser_tmp.add_argument("name_old", type=str, help="name of the source study")
    parser_tmp.add_argument("name_new", type=str, help="name of the destination study")
    parser_tmp = subparsers.add_parser("limit", help="limit the number of designs for a study")
    parser_tmp.add_argument("name", type=str, help="name of the study")
    parser_tmp.add_argument("limit", type=int, help="maximum number of designs")
    parser_tmp = subparsers.add_parser("import", help="import a dataset into the database")
    parser_tmp.add_argument("name", type=str, help="name of the study")
    parser_tmp.add_argument("file", type=str, help="filename of the dataset")
    parser_tmp = subparsers.add_parser("export", help="export a dataset from the database")
    parser_tmp.add_argument("name", type=str, help="name of the study")
    parser_tmp.add_argument("file", type=str, help="filename of the dataset")

    # parse
    args = parser.parse_args()

    # get database options
    data_database = data_common.get_database()

    # ask confirmation to prevent accidental damages
    if (args.command is not None) and (not args.quiet):
        status = input("database irreversible operation / confirm (y/n): ")
        if status != "y":
            sys.exit(0)

    # run database operation
    if args.command is None:
        manage.get_stat(data_database)
    elif args.command == "stat":
        manage.get_stat(data_database)
    elif args.command == "reset":
        manage.get_reset(data_database)
    elif args.command == "vacuum":
        manage.get_vacuum(data_database)
    elif args.command == "dump":
        manage.get_dump(data_database, args.filename)
    elif args.command == "restore":
        manage.get_restore(data_database, args.filename)
    elif args.command == "delete":
        manage.get_delete(data_database, args.name)
    elif args.command == "create":
        manage.get_create(data_database, args.name)
    elif args.command == "rename":
        manage.get_rename(data_database, args.name_old, args.name_new)
    elif args.command == "limit":
        manage.get_limit(data_database, args.name, args.limit)
    elif args.command == "import":
        manage.get_import(data_database, args.name, args.file)
    elif args.command == "export":
        manage.get_export(data_database, args.name, args.file)
    else:
        raise ValueError("invalid operation")

    # exit
    sys.exit(0)
