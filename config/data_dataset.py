"""
Parameters for generating a dataset:
    - with random inductor designs
    - with solenoid inductor designs
    - with spiral inductor designs
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import random
import numpy as np
from config import data_common


def _get_solenoid(param):
    """
    Create a solenoid.
    """

    # extract
    turn = param["turn"]
    width = param["width"]
    x_ext = param["x_ext"]
    y_ext = param["y_ext"]
    layer_low = param["layer_low"]
    layer_high = param["layer_high"]

    # get number of nodes
    n_wdg = 2*turn+1

    # get the layer position
    layer_wdg = np.empty(n_wdg-1, dtype=np.int64)
    layer_wdg[0::2] = layer_low
    layer_wdg[1::2] = layer_high

    # get the node x-coordinates
    x_wdg = np.linspace(+x_ext/2-width/2, -x_ext/2+width/2, n_wdg)

    # get the node y-coordinates
    y_wdg = np.empty(n_wdg, dtype=np.float64)
    y_wdg[0::2] = +y_ext/2-width/2
    y_wdg[1::2] = -y_ext/2+width/2

    # get trace width
    width_wdg = np.full(n_wdg, width, dtype=np.float64)

    # assemble the coordinates
    coord_wdg = np.vstack((x_wdg, y_wdg)).transpose()

    # assemble geometry
    data_coil = {
        "n_wdg": n_wdg,
        "coord_wdg": coord_wdg,
        "width_wdg": width_wdg,
        "layer_wdg": layer_wdg,
    }

    return data_coil


def _get_spiral(param):
    """
    Create a spiral.
    """

    # extract
    segment = param["segment"]
    width = param["width"]
    insulation = param["insulation"]
    x_ext = param["x_ext"]
    y_ext = param["y_ext"]
    layer = param["layer"]

    # get number of nodes
    n_wdg = segment+1

    # get the signs
    x_wdg = (x_ext/2-width/2)*np.array([-1, -1, +1, +1], dtype=np.float64)
    y_wdg = (y_ext/2-width/2)*np.array([-1, +1, +1, -1], dtype=np.float64)

    # get coord
    x_sign = np.array([-1, -1, +1, +1], dtype=np.float64)
    y_sign = np.array([-1, +1, +1, -1], dtype=np.float64)

    # repeat
    x_wdg = np.tile(x_wdg, segment)
    y_wdg = np.tile(y_wdg, segment)
    x_sign = np.tile(x_sign, segment)
    y_sign = np.tile(y_sign, segment)

    # offset
    offset_x = np.floor_divide(np.arange(4*segment+0), 4)
    offset_y = np.floor_divide(np.arange(4*segment-1), 4)
    offset_y = np.insert(offset_y, 0, 0)

    x_wdg -= x_sign*(width+insulation)*offset_x
    y_wdg -= y_sign*(width+insulation)*offset_y

    # limit
    x_wdg = x_wdg[0:segment+1]
    y_wdg = y_wdg[0:segment+1]

    # get the layer position
    layer_wdg = np.full(n_wdg-1, layer, dtype=np.int64)

    # get trace width
    width_wdg = np.full(n_wdg, width, dtype=np.float64)

    # assemble the coordinates
    coord_wdg = np.vstack((x_wdg, y_wdg)).transpose()

    # assemble geometry
    data_coil = {
        "n_wdg": n_wdg,
        "coord_wdg": coord_wdg,
        "width_wdg": width_wdg,
        "layer_wdg": layer_wdg,
    }

    return data_coil


def _get_sweep(sweep, _get_solenoid):
    """
    Span a sweep and generate many inductor geometries.
    """

    # extract sweep parameters
    keys = sweep.keys()
    values = sweep.values()
    sizes = [len(item) for item in values]

    # span the sweep values
    n_design = np.prod(sizes)
    matrices = np.meshgrid(*values)
    matrices = [item.flatten() for item in matrices]

    # init geometry list
    data_coil = []

    # compute the geometries
    for i in range(n_design):
        # assemble the arguments
        param_tmp = {}
        for j, name in enumerate(keys):
            param_tmp[name] = matrices[j][i]

        # construct the geometry
        data_coil_tmp = _get_solenoid(param_tmp)

        # add the geometry
        data_coil.append(data_coil_tmp)

    # shuffle the order
    random.shuffle(data_coil)

    return data_coil


def _get_array(shape):
    """
    Return the data for .
    """

    # assemble the parameters sweep
    if shape == "solenoid":
        sweep = {
            "turn": [2, 3, 4],
            "width": np.linspace(81.0e-6, 379.0e-6, 5),
            "x_ext": np.linspace(0.71e-3, 0.99e-3, 3),
            "y_ext": np.linspace(0.71e-3, 0.99e-3, 3),
            "layer_low": [0],
            "layer_high": [4],
        }
        fct_shape = _get_solenoid
    elif shape == "spiral":
        sweep = {
            "segment": [5, 6, 7, 8],
            "width": np.linspace(81.0e-6, 379.0e-6, 5),
            "insulation": np.linspace(31.0e-6, 129.0e-6, 3),
            "x_ext": np.linspace(0.71e-3, 0.99e-3, 3),
            "y_ext": np.linspace(0.71e-3, 0.99e-3, 3),
            "layer": [2],
        }
        fct_shape = _get_spiral
    else:
        raise ValueError("invalid shape")

    # get all the solenoid geometries
    data_coil = _get_sweep(sweep, fct_shape)

    # dataset generation options
    data_sweep = {
        "data_coil": data_coil,  # list with the inductor geometries to be computed
        "cond_solve": 0.0,  # constraint threshold for solving a design after applying the design rules
        "obj_keep": 0.6,  # objective function threshold for writing the designs in the database
    }

    return data_sweep


def get_param(config, shape, parallel):
    """
    Parameters for generating a dataset with solenoid inductor designs.
    """

    # get the inductor parameters
    param = data_common.get_param(config)

    # get database options
    data_database = data_common.get_database()

    # number of parallel processes
    n_parallel = int(parallel)

    # check the shape type
    if shape == "rand":
        # dataset generation method
        method_sweep = "rand"

        # dataset generation options
        data_sweep = {
            "n_run": int(10e3),  # number of random geometries to be generated
            "cond_gen": 0.0,  # constraint threshold for generating valid random geometries
            "cond_solve": 0.0,  # constraint threshold for solving a design after applying the design rules
            "obj_keep": 0.6,  # objective function threshold for writing the designs in the database
        }
    else:
        # dataset generation method
        method_sweep = "array"

        # dataset generation options
        data_sweep = _get_array(shape)

    # dataset computation options
    data_dataset = {
        "n_parallel": n_parallel,  # number of parallel processes
        "method_sweep": method_sweep,  # dataset generation method ("array" for specified designs)
        "delay_collect": 120.0,  # poll delays (in seconds) for flushing results into the database
        "delay_timeout": 1.0,  # timeout delays (in seconds) waiting results from the process pool
    }

    # append the data
    param["data_dataset"] = data_dataset
    param["data_sweep"] = data_sweep
    param["data_database"] = data_database

    return param
