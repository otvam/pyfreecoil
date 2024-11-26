"""
Parameters for computing a single design (user-defined).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np
from config import data_common


def get_param(config, shape):
    """
    Extract the best design from the dataset.
    """

    if shape == "solenoid":
        n_wdg = 5
        coord_wdg = [
            [+0.00038, +0.00038],
            [+0.00019, -0.00038],
            [+0.00000, +0.00038],
            [-0.00019, -0.00038],
            [-0.00038, +0.00038],
        ]
        width_wdg = [0.0002, 0.0002, 0.0002, 0.0002, 0.0002]
        layer_wdg = [0, 4, 0, 4]
    elif shape == "spiral":
        n_wdg = 6
        coord_wdg = [
            [+0.00038, +0.00038],
            [+0.00038, -0.00038],
            [-0.00038, -0.00038],
            [-0.00038, +0.00038],
            [+0.00008, +0.00038],
            [+0.00008, -0.00008],
        ]
        width_wdg = [0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002]
        layer_wdg = [2, 2, 2, 2, 2]
    else:
        raise ValueError("invalid shape")

    # global parameters
    #   - design_id: integer with a design ID
    #   - study_id: integer with a study ID
    data_id = {
        "design_id": 0,
        "study_id": 0,
    }

    # design geometry definition
    #   - n_wdg: size of the geometry (number of nodes)
    #   - coord_wdg: array with the coordinates of the nodes
    #   - width_wdg: array with the width of the nodes
    #   - layer_wdg: array with the layer position of the traces
    data_coil = {
        "n_wdg": n_wdg,
        "coord_wdg": np.array(coord_wdg, dtype=np.float64),
        "width_wdg": np.array(width_wdg, dtype=np.float64),
        "layer_wdg": np.array(layer_wdg, dtype=np.int64),
    }

    # get the inductor parameters
    param = data_common.get_param(config)

    # append the data
    param["data_id"] = data_id
    param["data_coil"] = data_coil

    return param
