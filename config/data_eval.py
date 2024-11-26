"""
Parameters for computing a single design (from a dataset).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

from config import data_common


def get_param(config, extract):
    """
    Extract the best design from the dataset.
    """

    # get the inductor parameters
    param = data_common.get_param(config)

    # filter the dataset
    def fct_filter(design):
        return design

    # extract a design
    def fct_extract(design):
        if extract == "best":
            # get the best design with respect to the objection function
            idx = design["obj"].idxmin()
            design = design.loc[idx]
        elif extract == "rand":
            # get a random design
            design = design.sample(n=1).squeeze()
        else:
            raise ValueError("invalid design extraction")

        return design

    # append the data
    param["fct_filter"] = fct_filter
    param["fct_extract"] = fct_extract

    return param


