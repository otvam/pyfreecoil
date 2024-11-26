"""
Parameters for retrieving and exporting inductor designs from the SQL database.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

from config import data_common


def get_param(name):
    """
    Parameters for retrieving and exporting inductor designs from the SQL database.
    """

    # get database options
    data_database = data_common.get_database()

    # dataset query
    #   - database query
    #       - limit: row limit for the query
    #       - offset: row offset for the query
    #       - random: random shuffle of the rows
    #       - name_list: list of study names for querying designs
    #   - query filtering
    #       - fct_process: function for filtering/sorting the designs
    #       - keep: maximum number of designs to be selected (if required)
    #       - order: rule for truncating the designs ("random", "head", or "tail")
    data_filter = [
        {
            "query": {"limit": None, "offset": None, "random": False, "name_list": [name]},
            "extract": [{"order": None, "keep": None, "fct_process": None}],
        }
    ]

    # append the data
    param = {
        "data_filter": data_filter,
        "data_database": data_database,
    }

    return param
