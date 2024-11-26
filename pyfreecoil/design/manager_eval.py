"""
Module for solving and inductor geometry and generating design data:
    - check the design rules
    - mesh and solve the PEEC problem
    - compute the converter operation
    - get the constraint function
    - get the objective function
    - query designs from the database
    - description of the design variables
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"


import numpy as np
import pandas as pd
from pyfreecoil.solver import solver
from pyfreecoil.design import manager_design
from pyfreecoil.design import manager_objective
from pyfreecoil.utils import manage_trace


def get_check(design, data_component):
    """
    Parse the geometry, check the design rules, add the results to the design.
    For exception handling, this method is generating a traceback and ignoring the exception.
    """

    try:
        data_coil = get_data_coil(design)
        data_vector = solver.run_parse(data_coil, data_component)
        data_valid = solver.run_check(data_vector, data_component)
        design = manager_design.add_data_valid(design, data_valid)
    except Exception as ex:
        args = (design, data_component)
        manage_trace.trace_error("check", get_check, args, ex)

    return design


def get_solve(design, data_component, data_tolerance):
    """
    Parse the geometry, run the mesher, run the solver, add the results to the design.
    For exception handling, this method is generating a traceback and ignoring the exception.
    """

    try:
        data_coil = get_data_coil(design)
        data_vector = solver.run_parse(data_coil, data_component)
        data_voxel = solver.run_mesh(data_vector, data_component)
        (data_solution, data_peec) = solver.run_solve(data_voxel, data_component, data_tolerance)
        design = manager_design.add_data_peec(design, data_peec)
    except Exception as ex:
        args = (design, data_component, data_tolerance)
        manage_trace.trace_error("solve", get_solve, args, ex)

    return design


def get_score(design, data_converter):
    """
    Parse the converter operation and add the results to the design.
    """

    design = manager_design.add_data_converter(design, data_converter)

    return design


def get_cond(design, data_objective):
    """
    Get the constraint function.
    """

    (cond, design) = manager_objective.get_cond(design, data_objective)

    return cond, design


def get_obj(design, data_objective):
    """
    Get the objective function.
    """

    (obj, design) = manager_objective.get_obj(design, data_objective)

    return obj, design


def get_design_extract(design, extract):
    """
    Filter design DataFrame with custom rules.
    """

    # extract
    order = extract["order"]
    keep = extract["keep"]
    fct_process = extract["fct_process"]

    # apply custom filter function
    if (fct_process is not None) and (not design.empty):
        design = fct_process(design)

    # pick designs (random or head/tail)
    if (keep is not None) and (not design.empty):
        if order is None:
            pass
        elif order == "random":
            design = design.sample(min(keep, len(design)))
        elif order == "head":
            design = design.iloc[:+keep]
        elif order == "tail":
            design = design.iloc[-keep:]
        else:
            raise ValueError("invalid order")

    return design


def get_design_filter(fct_query, data_filter):
    """
    Extract, filter, and assemble a design DataFrame.
    """

    # init list for the design datasets
    design_list = []

    for data_filter_tmp in data_filter:
        # extract
        query = data_filter_tmp["query"]
        extract = data_filter_tmp["extract"]

        # get database query
        design = fct_query(query)

        # filter the design datasets
        for extract_tmp in extract:
            # filter the dataset
            design_tmp = get_design_extract(design.copy(), extract_tmp)

            # append
            design_list.append(design_tmp)

    # concat, set index, remove duplicate, and sort
    design = pd.concat(design_list, axis=0)
    design = design.set_index("design_id", drop=False)
    design = design[~design.index.duplicated()]
    design = design.sort_index()

    return design


def set_data_coil(design, data_coil):
    """
    Set the coil geometry.
    """

    # extract
    n_wdg = data_coil["n_wdg"]
    coord_wdg = data_coil["coord_wdg"]
    width_wdg = data_coil["width_wdg"]
    layer_wdg = data_coil["layer_wdg"]

    # assign data
    design["n_wdg"] = n_wdg
    design["coord_wdg"] = coord_wdg
    design["width_wdg"] = width_wdg
    design["layer_wdg"] = layer_wdg

    return design


def set_data_id(design, data_id):
    """
    Set the design and study IDs.
    """

    # extract
    design_id = data_id["design_id"]
    study_id = data_id["study_id"]

    # assign data
    design["design_id"] = design_id
    design["study_id"] = study_id

    return design


def get_data_coil(design):
    """
    Extract the coil geometry.
    """

    # extract
    n_wdg = design["n_wdg"]
    coord_wdg = design["coord_wdg"]
    width_wdg = design["width_wdg"]
    layer_wdg = design["layer_wdg"]

    # assign data
    data_coil = {
        "n_wdg": n_wdg,
        "coord_wdg": coord_wdg,
        "width_wdg": width_wdg,
        "layer_wdg": layer_wdg,
    }

    return data_coil


def get_data_id(design):
    """
    Extract the design and study IDs.
    """

    # extract
    design_id = design["design_id"]
    study_id = design["study_id"]

    # assign data
    data_id = {
        "design_id": design_id,
        "study_id": study_id,
    }

    return data_id


def get_design_default():
    """
    Generate a default design structure with complete dummy data.
    """

    design = {
        # unique id
        "design_id": 0,
        "study_id": 0,
        # geom content
        "n_wdg": 0,
        "coord_wdg": np.empty((0, 2), dtype=np.float64),
        "width_wdg": np.empty(0, dtype=np.float64),
        "layer_wdg": np.empty(0, dtype=np.int64),
        # check content
        "valid_boundary": np.nan,
        "valid_clearance": np.nan,
        "valid_length": np.nan,
        "valid_width": np.nan,
        "valid_distance": np.nan,
        "valid_angle": np.nan,
        "valid_diff": np.nan,
        "valid_radius": np.nan,
        # solve content
        "f_vec": np.empty(0, dtype=np.float64),
        "R_vec": np.empty(0, dtype=np.float64),
        "L_vec": np.empty(0, dtype=np.float64),
        "H_vec": np.empty(0, dtype=np.float64),
        "J_vec": np.empty(0, dtype=np.float64),
        # score content
        "ripple_pkpk": np.nan,
        "eta_mag": np.nan,
        "eta_tot": np.nan,
        "A_sw": np.nan,
        "P_sw": np.nan,
        "P_add": np.nan,
        "P_mag": np.nan,
        "P_tot": np.nan,
        "I_tot": np.nan,
        "I_pkpk": np.nan,
        "J_tot": np.nan,
        "P_dc": np.nan,
        "P_ac": np.nan,
        "I_dc": np.nan,
        "I_ac": np.nan,
        "J_dc": np.nan,
        "J_ac": np.nan,
        "H_dc": np.nan,
        "H_ac": np.nan,
        # solution status
        "checked": False,
        "solved": False,
        "scored": False,
        # objective vector
        "validity_vec": np.empty(0, dtype=np.float64),
        "penalty_vec": np.empty(0, dtype=np.float64),
        "loss_vec": np.empty(0, dtype=np.float64),
        # objective content
        "cond": np.nan,
        "obj": np.nan,
    }

    return design


def get_var_sql():
    """
    Names and types of the variables stored in the database.
    """

    var_sql = [
        # geom content
        ("n_wdg", "int"),
        ("coord_wdg", "float_2D"),
        ("width_wdg", "float_1D"),
        ("layer_wdg", "int_1D"),
        # check content
        ("valid_boundary", "float"),
        ("valid_clearance", "float"),
        ("valid_length", "float"),
        ("valid_width", "float"),
        ("valid_distance", "float"),
        ("valid_angle", "float"),
        ("valid_diff", "float"),
        ("valid_radius", "float"),
        # solve content
        ("f_vec", "float_1D"),
        ("R_vec", "float_1D"),
        ("L_vec", "float_1D"),
        ("H_vec", "float_1D"),
        ("J_vec", "float_1D"),
        # score content
        ("ripple_pkpk", "float"),
        ("eta_mag", "float"),
        ("eta_tot", "float"),
        ("A_sw", "float"),
        ("P_sw", "float"),
        ("P_add", "float"),
        ("P_mag", "float"),
        ("P_tot", "float"),
        ("I_tot", "float"),
        ("I_pkpk", "float"),
        ("J_tot", "float"),
        ("P_dc", "float"),
        ("P_ac", "float"),
        ("I_dc", "float"),
        ("I_ac", "float"),
        ("J_dc", "float"),
        ("J_ac", "float"),
        ("H_dc", "float"),
        ("H_ac", "float"),
        # solution status
        ("checked", "bool"),
        ("solved", "bool"),
        ("scored", "bool"),
        # objective vector
        ("validity_vec", "float_1D"),
        ("penalty_vec", "float_1D"),
        ("loss_vec", "float_1D"),
        # objective content
        ("cond", "float"),
        ("obj", "float"),

    ]

    return var_sql
