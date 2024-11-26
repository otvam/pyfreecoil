"""
Module for managing the PostgreSQL database.
This code is assuming good faith usage (SQL injection).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import time
import psycopg2
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
        Get the credential for the PostreSQL command line utils.
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
    def _run_fetch(self, cmd, param):
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

    def _get_sql_query(self, query):
        """
        SQL filters for fetching designs.
        """

        # extract
        name_list = query["name_list"]
        limit = query["limit"]
        offset = query["offset"]
        random = query["random"]

        # SQL parameters
        param = []

        # parse filter study name
        if name_list:
            cmd_name = f"study_id in (SELECT study_id FROM {self.study} WHERE name in %s)"
            param.append(tuple(name_list))
        else:
            cmd_name = "TRUE"

        # parse limit directive
        if limit:
            cmd_limit = "LIMIT %s"
            param.append(limit)
        else:
            cmd_limit = "LIMIT ALL"

        # parse offset directive
        if offset:
            cmd_offset = "OFFSET %s"
            param.append(offset)
        else:
            cmd_offset = "OFFSET NULL"

        # assemble command
        if random:
            cmd = f"{cmd_name} ORDER BY RANDOM() {cmd_limit} {cmd_offset}"
        else:
            cmd = f"{cmd_name} {cmd_limit} {cmd_offset}"

        return cmd, param

    def _get_sql_get(self, name):
        """
        SQL filters for fetching designs.
        """

        # SQL parameters
        param = [name]

        # parse filter study name
        cmd = f"study_id in (SELECT study_id FROM {self.study} WHERE name = %s)"

        return cmd, param

    def _get_cmd_get_design(self, name):
        """
        Construct a SQL query for fetching designs.
        """

        # init design variables
        var = []

        # find design variables
        for (var_name, var_type) in self.var_sql:
            var.append(var_name)

        # assemble design variables
        var = ", ".join(var)

        # get design filter command and parameters
        (cmd, param) = self._get_sql_get(name)

        # assemble command
        cmd = f"(SELECT design_id, study_id, {var} FROM {self.design} WHERE {cmd})"

        return cmd, param

    def _get_cmd_get_query(self, query):
        """
        Construct a SQL query for fetching designs.
        """

        # init design variables
        var = []

        # find design variables
        for (var_name, var_type) in self.var_sql:
            var.append(var_name)

        # assemble design variables
        var = ", ".join(var)

        # get design filter command and parameters
        (cmd, param) = self._get_sql_query(query)

        # assemble command
        cmd = f"(SELECT design_id, study_id, {var} FROM {self.design} WHERE {cmd})"

        return cmd, param

    def _get_cmd_add_design(self, name):
        """
        Construct a SQL query for inserting designs.
        """

        # init design variables
        cmd_name = []
        cmd_insert = []

        # find design variables
        for (var_name, var_type) in self.var_sql:
            cmd_name.append(var_name)
            cmd_insert.append("%s")

        # assemble design variables
        cmd_name = ", ".join(cmd_name)
        cmd_insert = ", ".join(cmd_insert)

        # assemble command
        cmd = (
            f"INSERT INTO {self.design}(study_id, {cmd_name})\n"
            f"VALUES ((SELECT study_id FROM {self.study} WHERE name = %s), {cmd_insert})\n"
        )

        # SQL parameters with the study name
        param = [name]

        return cmd, param

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

    def _get_data_to_sql(self, data, param_cmd):
        """
        Transform a Dataframe into SQL designs (serialize).
        """

        # SQL parameters
        param_add = []

        # cast and serialize the design parameters
        for (var_name, var_type) in self.var_sql:
            # cast and serialize
            if var_name in data:
                var = data[var_name]
                var = _get_sql_cast(var_type, var)
            else:
                var = None

            # add value
            param_add.append(var)

        # assemble
        param = param_cmd + param_add

        return param

    def get_stat(self):
        """
        Get statistics about the number of studies and designs.
        Get the total database size.
        """

        # get command
        cmd = (
            f"SELECT\n"
            f"(SELECT pg_database_size(current_database())) AS n_total_byte,\n"
            f"(SELECT pg_total_relation_size('{self.study}')) AS n_study_byte,\n"
            f"(SELECT pg_total_relation_size('{self.design}')) AS n_design_byte,\n"
            f"(SELECT COUNT(*) FROM {self.study}) AS n_study,\n"
            f"(SELECT COUNT(*) FROM {self.design}) AS n_design\n"
        )

        # execute query
        data = self.sql._run_fetch(cmd, [])

        # extract results
        (n_total_byte, n_study_byte, n_design_byte, n_study, n_design) = data[0]

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
            f"SELECT {self.study}.name, COUNT({self.design}.study_id) AS count\n"
            f"FROM {self.study}\n"
            f"LEFT JOIN {self.design} ON {self.design}.study_id = {self.study}.study_id\n"
            f"GROUP BY {self.study}.study_id\n"
        )

        # execute query
        data = self.sql._run_fetch(cmd, [])

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
            f"DROP TABLE IF EXISTS {self.design};\n"
            f"DROP TABLE IF EXISTS {self.study};\n"
        )

        # execute query
        self.sql.run_cmd(cmd, [])

    def create_db(self):
        """
        Create the database (study and design tables).
        """

        # init design variables
        var = []

        # parse design variables
        for (var_name, var_type) in self.var_sql:
            sql_type = _get_sql_type(var_type)
            var.append("%s %s NOT NULL" % (var_name, sql_type))

        # assemble design variables
        var = ", ".join(var)

        # get command
        cmd = (
            f"CREATE TABLE IF NOT EXISTS {self.study} (\n"
            f"    study_id SERIAL PRIMARY KEY,\n"
            f"    name VARCHAR NOT NULL,\n"
            f"    UNIQUE(name)\n"
            f");\n"
            f"CREATE TABLE IF NOT EXISTS {self.design} (\n"
            f"    design_id SERIAL PRIMARY KEY,\n"
            f"    study_id INTEGER NOT NULL,\n"
            f"    {var},\n"
            f"    CONSTRAINT fk\n"
            f"        FOREIGN KEY(study_id)\n"
            f"        REFERENCES {self.study}(study_id)\n"
            f");\n"
        )

        # execute query
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
            f"INSERT INTO {self.study}(name)\n"
            f"VALUES (%s)\n"
            f"ON CONFLICT DO NOTHING\n"
        )

        # execute query
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
            f"DELETE FROM {self.design}\n"
            f"WHERE study_id = (SELECT study_id FROM {self.study} WHERE name = %s);\n"
            f"DELETE FROM {self.study}\n"
            f"WHERE name = %s;\n"
        )

        # execute query
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
            f"UPDATE {self.study}\n"
            f"SET name = %s\n"
            f"WHERE name = %s\n"
        )

        # execute query
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
            f"DELETE FROM {self.design}\n"
            f"WHERE ctid IN (\n"
            f"    SELECT ctid\n"
            f"    FROM {self.design}\n"
            f"    WHERE study_id = (SELECT study_id FROM {self.study} WHERE name = %s)\n"
            f"    OFFSET %s\n"
            f")\n"
        )

        # execute query
        self.sql.run_cmd(cmd, [name, limit])

    def add_design(self, name, data):
        """
        Add new designs to the database.
        """

        # get base command
        (cmd, param_cmd) = self._get_cmd_add_design(name)

        # get the serialized parameters
        param = []
        for idx_tmp, data_tmp in data.iterrows():
            param_tmp = self._get_data_to_sql(data_tmp, param_cmd)
            param.append(param_tmp)

        # execute query
        self.sql.run_batch(cmd, param)

    def get_design(self, name):
        """
        Query designs and apply a custom function to the extracted data.
        """

        # get command
        (cmd, param) = self._get_cmd_get_design(name)

        # execute query
        data = self.sql._run_fetch(cmd, param)

        # deserialize
        data = self._get_data_from_sql(data)

        return data

    def get_query(self, query):
        """
        Query designs and apply a custom function to the extracted data.
        """

        # get command
        (cmd, param) = self._get_cmd_get_query(query)

        # execute query
        data = self.sql._run_fetch(cmd, param)

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
