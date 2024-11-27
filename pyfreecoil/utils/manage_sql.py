"""
Module for managing the PostgreSQL database.

The database consists of two tables:
    - the "study" table contains the design categories
    - the "design" table contains the actual designs
    - both tables linked with a foreign key
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import time
import psycopg2
import psycopg2.sql
import psycopg2.extras
import pandas as pd
import numpy as np
import subprocess


def _get_sql_type(var_type):
    """
    Get the corresponding SQL type from a data type.
    """

    if var_type == "int":
        sql_type = "INTEGER"
    elif var_type == "float":
        sql_type = "REAL"
    elif var_type == "bool":
        sql_type = "BOOLEAN"
    elif var_type == "int_1D":
        sql_type = "INTEGER[]"
    elif var_type == "int_2D":
        sql_type = "INTEGER[][]"
    elif var_type == "float_1D":
        sql_type = "REAL[]"
    elif var_type == "float_2D":
        sql_type = "REAL[][]"
    elif var_type == "bool_1D":
        sql_type = "BOOLEAN[]"
    elif var_type == "bool_2D":
        sql_type = "BOOLEAN[][]"
    else:
        raise ValueError("invalid type")

    return sql_type


def _get_sql_cast(var_type, var):
    """
    Transform data from Python to SQL format.
    """

    # check
    if var is None:
        return var

    # parse
    if var_type == "int":
        var = int(var)
    elif var_type == "float":
        var = float(var)
    elif var_type == "bool":
        var = bool(var)
    elif var_type in ["int_1D", "int_2D"]:
        var = np.array(var, dtype=np.int64).tolist()
    elif var_type in ["float_1D", "float_2D"]:
        var = np.array(var, dtype=np.float64).tolist()
    elif var_type in ["bool_1D", "bool_2D"]:
        var = np.array(var, dtype=bool).tolist()
    else:
        raise ValueError("invalid type")

    return var


def _get_df_cast(var_type, var):
    """
    Transform data from SQL to Python format.
    """

    # check
    if var is None:
        return var

    # parse
    if var_type == "int":
        var = var.astype(int)
    elif var_type == "bool":
        var = var.astype(bool)
    elif var_type == "float":
        var = var.astype(float)
    elif var_type in ["int_1D", "int_2D"]:
        var = var.apply(lambda row: np.array(row, dtype=np.int64))
    elif var_type in ["float_1D", "float_2D"]:
        var = var.apply(lambda row: np.array(row, dtype=np.float64))
    elif var_type in ["bool_1D", "bool_2D"]:
        var = var.apply(lambda row: np.array(row, dtype=bool))
    else:
        raise ValueError("invalid type")

    return var


class _PostgreSql:
    """
    Class managing the connection to the PostgreSQL database.
    Automatic reconnection after connection failures.
    """

    def __init__(self, credential, session, connection, robust):
        """
        Constructor.
        """

        # assign credential and session parameters
        self.credential = credential
        self.session = session
        self.robust = robust

        # assign connection parameters
        self.retry = connection["retry"]
        self.delay = connection["delay"]

        # connection init
        self.conn = None

    @staticmethod
    def _retry_fail(function):
        """
        Decorator executing a SQL function.
        Reconnect and retry on failures.
        """

        def wrap_function(self, *args):
            """
            Run the decorated function.
            Reconnected and retry if necessary.
            """

            try:
                # try the operation with the existing connection
                return function(self, *args)
            except psycopg2.OperationalError as ex:
                # abort immediately without retries
                if not self.robust:
                    raise ex

                # reconnect and retry the operation
                for i in range(self.retry):
                    try:
                        # close old connection
                        self.close()

                        # restart a new connection
                        self.connect()

                        # retry the operation
                        return function(self, *args)
                    except psycopg2.Error:
                        time.sleep(self.delay)

                # failure after number of retry is exceeded
                raise ex

        return wrap_function

    def connect(self):
        """
        Create a connection to the database.
        """

        self.conn = psycopg2.connect(**self.credential)
        self.conn.set_session(**self.session)

    def close(self):
        """
        Close a connection to the database.
        """

        self.conn.close()

    def get_credential(self):
        """
        Get the credential for the PostgreSQL command line utils.
        """

        # command line options for the server
        opt = [
            "-h", self.credential["host"],
            "-p", self.credential["port"],
            "-d", self.credential["database"],
        ]

        # env variables for the credentials
        env = {
            "PGUSER": self.credential["user"],
            "PGPASSWORD": self.credential["password"],
        }

        return opt, env

    @_retry_fail
    def run_cmd(self, cmd, param):
        """
        Run a SQL command (without results).
        """

        with self.conn.cursor() as cursor:
            cursor.execute(cmd, param)

    @_retry_fail
    def run_batch(self, cmd, param):
        """
        Run several SQL commands (without results).
        """

        with self.conn.cursor() as cursor:
            psycopg2.extras.execute_batch(cursor, cmd, param)

    @_retry_fail
    def run_fetch(self, cmd, param):
        """
        Run a SQL command and fetch all the results.
        """

        with self.conn.cursor() as cursor:
            cursor.execute(cmd, param)
            data = cursor.fetchall()

        return data


class ManageSql:
    """
    Class managing the database (studies and designs).
    Manage the database (create, reset, backup, etc.).
    Add and fetch studies and designs.
    Get statistics about the usage.
    """

    def __init__(self, data_database, var_sql, robust):
        """
        Constructor.
        """

        # extract
        credential = data_database["credential"]
        connection = data_database["connection"]
        session = data_database["session"]

        # assign
        self.study = data_database["study"]
        self.design = data_database["design"]

        # object managing the database connection
        self.sql = _PostgreSql(credential, session, connection, robust)
        
        # assign the variable description
        self.var_sql = var_sql

    def connect(self):
        """
        Create a connection to the database.
        """

        self.sql.connect()

    def close(self):
        """
        Close a connection to the database.
        """

        self.sql.close()

    def _get_query_table(self, cmd):
        """
        Format a SQL query (replace table names and design variable names.
        """

        # SQL commands for creating the table
        var_type = []

        # SQL command with the variable names
        var_name = []

        # SQL command with variable placeholders
        var_insert = []

        # find design variable substitution
        for (var_name_tmp, var_type_tmp) in self.var_sql:
            var_type.append(psycopg2.sql.SQL("{var_name_tmp} {sql_type_tmp} NOT NULL").format(
                var_name_tmp=psycopg2.sql.Identifier(var_name_tmp.lower()),
                sql_type_tmp=psycopg2.sql.SQL(_get_sql_type(var_type_tmp))
            ))
            var_name.append(psycopg2.sql.Identifier(var_name_tmp.lower()))
            var_insert.append(psycopg2.sql.Placeholder())

        # construct the SQL query
        cmd = psycopg2.sql.SQL(cmd).format(
            study=psycopg2.sql.Identifier(self.study),
            design=psycopg2.sql.Identifier(self.design),
            var_type=psycopg2.sql.SQL(', ').join(var_type),
            var_name=psycopg2.sql.SQL(', ').join(var_name),
            var_insert=psycopg2.sql.SQL(', ').join(var_insert),
        )

        return cmd

    def _get_data_from_sql(self, data):
        """
        Transform SQL designs into a DataFrame (deserialize).
        """

        # get all design variables
        var = ["design_id", "study_id"]
        for (var_name, var_type) in self.var_sql:
            var.append(var_name)

        # create DataFrame
        data = pd.DataFrame(data, columns=var)

        # cast and deserialize
        for (var_name, var_type) in self.var_sql:
            data[var_name] = _get_df_cast(var_type, data[var_name])

        return data

    def _get_data_to_sql(self, data):
        """
        Transform a Dataframe into SQL designs (serialize).
        """

        # SQL parameters
        param = []

        # cast and serialize the design parameters
        for (var_name, var_type) in self.var_sql:
            # cast and serialize
            if var_name in data:
                var = data[var_name]
                var = _get_sql_cast(var_type, var)
            else:
                var = None

            # add value
            param.append(var)

        return param

    def get_stat(self):
        """
        Get statistics about the number of studies and designs.
        Get the total database and table size.
        """

        # get command
        cmd = (
            "SELECT\n"
            "(SELECT pg_database_size(current_database())) AS n_total_byte,\n"
            "(SELECT pg_total_relation_size('{study}')) AS n_study_byte,\n"
            "(SELECT pg_total_relation_size('{design}')) AS n_design_byte,\n"
            "(SELECT COUNT(*) FROM {study}) AS n_study,\n"
            "(SELECT COUNT(*) FROM {design}) AS n_design\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        data = self.sql.run_fetch(cmd, [])

        # extract results
        (n_total_byte, n_study_byte, n_design_byte, n_study, n_design) = data.pop()

        # total size of the tables
        n_table_byte = n_study_byte+n_design_byte

        # assemble
        stat = {
            "study": self.study,
            "design": self.design,
            "n_total_byte": n_total_byte,
            "n_table_byte": n_table_byte,
            "n_study": n_study,
            "n_design": n_design,
        }

        return stat

    def get_study(self):
        """
        Get a dictionary with the study and the number of designs.
        """

        # get command
        cmd = (
            "SELECT {study}.name, COUNT({design}.study_id) AS count\n"
            "FROM {study}\n"
            "LEFT JOIN {design} ON {design}.study_id = {study}.study_id\n"
            "GROUP BY {study}.study_id\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        data = self.sql.run_fetch(cmd, [])

        # extract study and number of designs
        study = {}
        for name, n_design in data:
            study[name] = n_design

        # sort the dictionary
        study = dict(sorted(study.items()))

        return study

    def delete_db(self):
        """
        Delete the database (study and design tables).
        """

        # get command
        cmd = (
            "DROP TABLE IF EXISTS {design};\n"
            "DROP TABLE IF EXISTS {study};\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        self.sql.run_cmd(cmd, [])

    def create_db(self):
        """
        Create the database (study and design tables).
        """

        # get command
        cmd = (
            "CREATE TABLE IF NOT EXISTS {study} (\n"
            "    study_id SERIAL PRIMARY KEY,\n"
            "    name VARCHAR NOT NULL,\n"
            "    UNIQUE(name)\n"
            ");\n"
            "CREATE TABLE IF NOT EXISTS {design} (\n"
            "    design_id SERIAL PRIMARY KEY,\n"
            "    study_id INTEGER NOT NULL,\n"
            "    {var_type},\n"
            "    CONSTRAINT fk\n"
            "        FOREIGN KEY(study_id)\n"
            "        REFERENCES {study}(study_id)\n"
            ");\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        self.sql.run_cmd(cmd, [])

    def create_study(self, name):
        """
        Create a new study.
        """

        # check
        if name is None:
            return

        # get command
        cmd = (
            "INSERT INTO {study}(name)\n"
            "VALUES (%s)\n"
            "ON CONFLICT DO NOTHING\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        self.sql.run_cmd(cmd, [name])

    def delete_study(self, name):
        """
        Delete a study.
        """

        # check
        if name is None:
            return

        # get command
        cmd = (
            "DELETE FROM {design}\n"
            "WHERE study_id = (SELECT study_id FROM {study} WHERE name = %s);\n"
            "DELETE FROM {study}\n"
            "WHERE name = %s;\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        self.sql.run_cmd(cmd, [name, name])

    def rename_study(self, name_old, name_new):
        """
        Rename a study.
        """

        # check
        if (name_old is None) or (name_new is None):
            return

        # get command
        cmd = (
            "UPDATE {study}\n"
            "SET name = %s\n"
            "WHERE name = %s\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        self.sql.run_cmd(cmd, [name_new, name_old])

    def limit_study(self, name, limit):
        """
        Limit the number of designs for a study (truncation).
        """

        # check
        if (name is None) or (limit is None):
            return

        # get command
        cmd = (
            "DELETE FROM {design}\n"
            "WHERE ctid IN (\n"
            "    SELECT ctid\n"
            "    FROM {design}\n"
            "    WHERE study_id = (SELECT study_id FROM {study} WHERE name = %s)\n"
            "    OFFSET %s\n"
            ")\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        self.sql.run_cmd(cmd, [name, limit])

    def add_design(self, name, data):
        """
        Add new designs to an existing study.
        """

        # get command
        cmd = (
            "INSERT INTO {design}(study_id, {var_name})\n"
            "VALUES ((SELECT study_id FROM {study} WHERE name = %s), {var_insert})\n"
        )

        # get the serialized parameters
        param = []
        for idx_tmp, data_tmp in data.iterrows():
            param_tmp = self._get_data_to_sql(data_tmp)
            param.append([name] + param_tmp)

        # execute query
        cmd = self._get_query_table(cmd)
        self.sql.run_batch(cmd, param)

    def get_design(self, name):
        """
        Get all the designs for a given study.
        """

        # assemble where command
        cmd = (
            "SELECT * FROM {design}\n"
            "WHERE study_id in (SELECT study_id FROM {study} WHERE name = %s)\n"
        )

        # execute query
        cmd = self._get_query_table(cmd)
        data = self.sql.run_fetch(cmd, [name])

        # deserialize
        data = self._get_data_from_sql(data)

        return data

    def get_query(self, query):
        """
        Query designs from the database (custom query).
        """

        # extract
        name_list = query["name_list"]
        limit = query["limit"]
        offset = query["offset"]
        random = query["random"]

        # SQL parameters
        param = []

        # parse filter study name
        cmd_name = "study_id in (SELECT study_id FROM {study} WHERE name in %s)"
        param.append(tuple(name_list))

        # parse limit directive
        if limit:
            cmd_limit = "LIMIT %s"
            param.append(limit)
        else:
            cmd_limit = "LIMIT NULL"

        # parse offset directive
        if offset:
            cmd_offset = "OFFSET %s"
            param.append(offset)
        else:
            cmd_offset = "OFFSET NULL"

        # assemble where command
        if random:
            cmd_order = "ORDER BY RANDOM()"
        else:
            cmd_order = "ORDER BY design_id"

        # assemble command (injection safe)
        cmd = "SELECT * FROM {design} WHERE %s %s %s %s" % (cmd_name, cmd_order, cmd_limit, cmd_offset)

        # execute query
        cmd = self._get_query_table(cmd)
        data = self.sql.run_fetch(cmd, param)

        # deserialize
        data = self._get_data_from_sql(data)

        return data

    def vacuum(self):
        """
        Vacuum the complete database.
        """

        # get credential
        (opt, env) = self.sql.get_credential()

        # vacuum command
        cmd = ["vacuumdb", "--quiet", "--full", "--table", self.design, "--table", self.study]

        # vacuum the database
        subprocess.run(
            cmd+opt,
            env=env,
            check=True,
        )

    def dump(self, filename):
        """
        Create a dump of the database.
        """

        # check file
        try:
            with open(filename, mode='wb'):
                pass
        except OSError:
            raise RuntimeError("invalid filename for the database dump")

        # get credential
        (opt, env) = self.sql.get_credential()

        # dump command
        cmd = ["pg_dump", "-Fc", "-f", filename]

        # dump the database
        subprocess.run(
            cmd+opt,
            env=env,
            check=True,
        )

    def restore(self, filename):
        """
        Restore the database from a dump.
        """

        # check file
        try:
            with open(filename, mode='rb'):
                pass
        except OSError:
            raise RuntimeError("invalid filename for the database dump")

        # get credential
        (opt, env) = self.sql.get_credential()

        # restore command
        cmd = ["pg_restore", "--clean", "--if-exists", "--no-privileges", filename]

        # restore the database
        subprocess.run(
            cmd+opt,
            env=env,
            check=True,
        )
