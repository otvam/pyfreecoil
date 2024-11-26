"""
Module for managing planar inductor designs:
    - generate the geometry from the coil description
    - check the design rules
    - mesh the geometry
    - solve the geometry
    - extract the results
    - plot the coil geometry
    - plot the mesher results
    - plot the solver results
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import os
import pypeec
import matplotlib.pyplot as plt
from pyfreecoil.solver import geometry_vector
from pyfreecoil.solver import geometry_check
from pyfreecoil.solver import geometry_plot
from pyfreecoil.solver import pypeec_mesher
from pyfreecoil.solver import pypeec_solver
from pyfreecoil.solver import pypeec_extract


def run_parse(data_coil, data_component):
    """
    Transform a coil geometry into shapes and layers.
    """

    # extract data
    size = data_component["size"]
    terminal = data_component["terminal"]
    shapely = data_component["shapely"]
    position = data_component["position"]
    outline = data_component["outline"]
    keepout = data_component["keepout"]

    # generate shapes
    data_vector = geometry_vector.get_data(data_coil, size, terminal, shapely, position, outline, keepout)

    return data_vector


def run_check(data_vector, data_component):
    """
    Check the compatibility of a geometry with the design rules.
    """

    # extract data
    design_rule = data_component["design_rule"]
    shapely = data_component["shapely"]

    # check design rules
    data_valid = geometry_check.run_check(data_vector, shapely, design_rule)

    return data_valid


def run_mesh(data_vector, data_component):
    """
    Run the PyPEEC mesher for a geometry (voxelization).
    """

    # extract data
    voxel = data_component["voxel"]
    mesh = data_component["mesh"]
    cloud = data_component["cloud"]

    # generate data
    data_geometry = pypeec_mesher.get_data(data_vector, voxel, mesh, cloud)

    # run mesher
    data_voxel = pypeec.run_mesher_data(data_geometry)

    return data_voxel


def run_solve(data_voxel, data_component, data_tolerance):
    """
    Run the PyPEEC solver for a geometry (field simulation).
    Extract features from the obtained results (mesher and solver).
    """

    # extract data
    excitation = data_component["excitation"]
    processing = data_component["processing"]

    # generate data
    data_problem = pypeec_solver.get_data(excitation)

    # run solver
    data_solution = pypeec.run_solver_data(data_voxel, data_problem, data_tolerance)

    # extract and parse the results
    data_peec = pypeec_extract.get_final(data_voxel, data_solution, processing)

    return data_solution, data_peec


def write_shaper(folder, data_vector, data_shaper):
    """
    Plot the inductor geometry (2D plots).
    Save the plots into files.
    """

    # extract data
    param_shared = data_shaper["param_shared"]
    param_mask = data_shaper["param_mask"]
    param_shape = data_shaper["param_shape"]
    param_terminal = data_shaper["param_terminal"]

    # run the plots
    geometry_plot.run_mask(data_vector, param_shared, param_mask)
    geometry_plot.run_terminal(data_vector, param_shared, param_terminal)
    geometry_plot.run_shape(data_vector, param_shared, param_shape)

    # save the plots
    fig_list = plt.get_fignums()
    for fig in fig_list:
        plt.figure(fig)
        plt.savefig(os.path.join(folder, "shaper_%d.png" % fig), dpi=500)

    # close the plots
    plt.close('all')


def write_viewer(folder, data_voxel, data_viewer):
    """
    Plot the PyPEEC mesher solution (3D plots).
    Save the plots into files.
    """

    pypeec.run_viewer_data(
        data_voxel,
        data_viewer,
        plot_mode="save",
        folder=folder,
        name="viewer",
    )


def write_plotter(folder, data_solution, data_plotter):
    """
    Plot the PyPEEC solver solution (3D plots).
    Save the plots into files.
    """

    pypeec.run_plotter_data(
        data_solution,
        data_plotter,
        plot_mode="save",
        folder=folder,
        name="plotter",
    )
