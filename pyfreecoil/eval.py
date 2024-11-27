"""
Script for computing a single inductor design.
Save the results (data, log, and plots) into files.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import os
import scisave
import scilogger
from pyfreecoil.solver import solver
from pyfreecoil.design import manager_eval
from pyfreecoil.design import manager_design
from pyfreecoil.design import manager_objective
from pyfreecoil.design import serialize_design

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def _get_run_design(folder, data_id, data_coil, eval_param):
    """
    Solve an inductor design:
        - generate the design data structure
        - parse the geometry and run the design rules
        - run the PEEC mesher and solver
    """

    data_component = eval_param["data_component"]
    data_tolerance = eval_param["data_tolerance"]
    data_viewer = eval_param["data_viewer"]
    data_plotter = eval_param["data_plotter"]
    data_shaper = eval_param["data_shaper"]

    LOGGER.info("create design")
    design = manager_eval.get_design_default()
    design = manager_eval.set_data_coil(design, data_coil)
    design = manager_eval.set_data_id(design, data_id)

    LOGGER.info("parse and check")
    data_vector = solver.run_parse(data_coil, data_component)
    data_valid = solver.run_check(data_vector, data_component)

    LOGGER.info("write results")
    design = manager_design.add_data_valid(design, data_valid)
    solver.write_shaper(folder, data_vector, data_shaper)
    scisave.write_data(os.path.join(folder, "data_coil.pck"), data_coil)
    scisave.write_data(os.path.join(folder, "data_valid.pck"), data_valid)
    scisave.write_data(os.path.join(folder, "data_vector.pck"), data_vector)

    LOGGER.info("run the PyPEEC mesher")
    data_voxel = solver.run_mesh(data_vector, data_component)

    LOGGER.info("run the PyPEEC solver")
    (data_solution, data_peec) = solver.run_solve(data_voxel, data_component, data_tolerance)

    LOGGER.info("write results")
    design = manager_design.add_data_peec(design, data_peec)
    solver.write_viewer(folder, data_voxel, data_viewer)
    solver.write_plotter(folder, data_solution, data_plotter)
    scisave.write_data(os.path.join(folder, "data_voxel.pck"), data_voxel)
    scisave.write_data(os.path.join(folder, "data_solution.pck"), data_solution)
    scisave.write_data(os.path.join(folder, "data_peec.pck"), data_peec)

    return design


def _get_postproc_design(folder, design, eval_param):
    """"
    Postprocess an inductor design:
        - compute the converter operation
        - compute the constraint and objection functions
        - save the results into files
    """

    # extract data
    data_converter = eval_param["data_converter"]
    data_objective = eval_param["data_objective"]

    LOGGER.info("compute converter")
    design = manager_design.add_data_converter(design, data_converter)

    LOGGER.info("compute constraint")
    (cond, design) = manager_objective.get_cond(design, data_objective)

    LOGGER.info("compute objective")
    (obj, design) = manager_objective.get_obj(design, data_objective)

    # write data
    LOGGER.info("write design")
    scisave.write_data(os.path.join(folder, "design.pck"), design)

    LOGGER.info("write json")
    scisave.write_data(os.path.join(folder, "design.json"), design)

    LOGGER.info("write txt")
    str_list = serialize_design.get_disp_str(design)
    with open(os.path.join(folder, "design.txt"), "w") as fid:
        for tmp in str_list:
            fid.write(tmp + "\n")

    str_list = serialize_design.get_disp_str(design)
    for tmp in str_list:
        LOGGER.info(tmp)


def get_run(file, folder, eval_param):
    """
    Module for computing and a single inductor design.
    Save the results (datasets and plots) into files.
    """

    LOGGER.info("====================== START: %s" % folder)

    # extract
    fct_filter = eval_param["fct_filter"]
    fct_extract = eval_param["fct_extract"]

    # load the dataset file
    design = scisave.load_data(file)

    # create folder
    os.makedirs(folder, exist_ok=True)

    # get the design
    design = fct_filter(design)
    design = fct_extract(design)

    # extract the design
    data_coil = manager_eval.get_data_coil(design)
    data_id = manager_eval.get_data_id(design)

    # evaluate the design
    design = _get_run_design(folder, data_id, data_coil, eval_param)

    # postprocess the design
    _get_postproc_design(folder, design, eval_param)

    LOGGER.info("====================== END: %s" % folder)


def get_design(folder, eval_param):
    """
    Module for computing and a single inductor design.
    Save the results (datasets and plots) into files.
    """

    LOGGER.info("====================== START: %s" % folder)

    # extract
    data_id = eval_param["data_id"]
    data_coil = eval_param["data_coil"]

    # create folder
    os.makedirs(folder, exist_ok=True)

    # evaluate the design
    design = _get_run_design(folder, data_id, data_coil, eval_param)

    # postprocess the design
    _get_postproc_design(folder, design, eval_param)

    LOGGER.info("====================== END: %s" % folder)
