"""
Module with utils managing the SQL database:
    - dump/restore/vacuum database
    - reset/create database
    - manage studies
    - show statistics
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import scisave
import scilogger
from pyfreecoil.design import manager_eval
from pyfreecoil.utils import manage_sql

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def get_dump(data_database, filename):
    """
    Backup the database in a file (dump).
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)

    LOGGER.info("dump / db")
    obj_sql.dump(filename)

    LOGGER.info("====================== END: manage")


def get_restore(data_database, filename):
    """
    Restore the database from a file (restore).
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)

    LOGGER.info("restore / db")
    obj_sql.restore(filename)

    LOGGER.info("====================== END: manage")


def get_vacuum(data_database):
    """
    Vacuum the database.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("vacuum / db")
    obj_sql.vacuum()

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_reset(data_database):
    """
    Reset the database (delete and create).
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("delete / db")
    obj_sql.delete_db()

    LOGGER.info("init / db")
    obj_sql.create_db()

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_delete(data_database, name):
    """
    Delete a study.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("delete / study")
    obj_sql.delete_study(name)

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_create(data_database, name):
    """
    Create a study.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("create / study")
    obj_sql.create_study(name)

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_rename(data_database, name_old, name_new):
    """
    Rename a study.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("rename / study")
    obj_sql.rename_study(name_old, name_new)

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_limit(data_database, name, limit):
    """
    Limit the number of designs for a study.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("limit / study")
    obj_sql.limit_study(name, limit)

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_import(data_database, name, file):
    """
    Insert a dataset into the database.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    # load the dataset
    LOGGER.info("load / dataset")
    design = scisave.load_data(file)

    LOGGER.info("insert / design")
    obj_sql.add_design(name, design)

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_export(data_database, name, file):
    """
    Export a dataset from the database.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("get / design")
    design = obj_sql.get_design(name)

    # load the dataset
    LOGGER.info("save / design")
    scisave.write_data(file, design)

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")


def get_stat(data_database):
    """
    Show database statistics.
    """

    LOGGER.info("====================== START: manage")

    LOGGER.info("connect")
    var_sql = manager_eval.get_var_sql()
    obj_sql = manage_sql.ManageSql(data_database, var_sql, False)
    obj_sql.connect()

    LOGGER.info("get statistics")
    stat = obj_sql.get_stat()
    study = obj_sql.get_study()

    LOGGER.info("show table")
    with LOGGER.BlockIndent():
        LOGGER.info("study = %s" % stat["study"])
        LOGGER.info("design = %s" % stat["design"])

    LOGGER.info("show table size")
    with LOGGER.BlockIndent():
        LOGGER.info("n_study = %d" % stat["n_study"])
        LOGGER.info("n_design = %d" % stat["n_design"])

    LOGGER.info("show disk size")
    with LOGGER.BlockIndent():
        LOGGER.info("space_total = %.1f MB" % (stat["n_total_byte"]/(1024**2)))
        LOGGER.info("space_table = %.1f MB" % (stat["n_table_byte"]/(1024**2)))

    LOGGER.info("show study")
    with LOGGER.BlockIndent():
        for name, n_design in study.items():
            LOGGER.info("%s = %d" % (name, n_design))

    LOGGER.info("close")
    obj_sql.close()

    LOGGER.info("====================== END: manage")
