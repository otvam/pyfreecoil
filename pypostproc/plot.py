"""
Display the PyPEEC plots (viewer and plotter).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import os
import sys
import argparse
import scilogger
import pypeec

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def run_save(filename_voxel, filename_solution, cfg_viewer, cfg_plotter, folder_out):
    """
    Run the PyPEEC viewer/plotter and save the results.
    """

    LOGGER.info("run/save the PyPEEC viewer")
    pypeec.run_viewer_file(
        filename_voxel,
        cfg_viewer,
        folder=folder_out,
        plot_mode="save",
        name="viewer",
    )

    LOGGER.info("run/save the PyPEEC plotter")
    pypeec.run_plotter_file(
        filename_solution,
        cfg_plotter,
        folder=folder_out,
        plot_mode="save",
        name="plotter",
    )


def run_show(filename_voxel, filename_solution, cfg_viewer, cfg_plotter):
    """
    Run the PyPEEC viewer/plotter and show the results.
    """

    LOGGER.info("run/show the PyPEEC viewer")
    pypeec.run_viewer_file(
        filename_voxel,
        cfg_viewer,
        plot_mode="qt",
    )

    LOGGER.info("run/show the PyPEEC plotter")
    pypeec.run_plotter_file(
        filename_solution,
        cfg_plotter,
        plot_mode="qt",
    )


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_in", required=True, type=str, help="folder with the evaluated design")
    parser.add_argument("--folder_out", required=True, type=str, help="folder for the results (to be created)")
    parser.add_argument("--cfg_viewer", required=True, type=str, help="configuration file for the viewer")
    parser.add_argument("--cfg_plotter", required=True, type=str, help="configuration file for the plotter")

    # parse arguments
    args = parser.parse_args()
    folder_in = args.folder_in
    folder_out = args.folder_out
    cfg_viewer = args.cfg_viewer
    cfg_plotter = args.cfg_plotter

    # create the output folder
    os.makedirs(folder_out, exist_ok=True)

    # results files
    filename_voxel = os.path.join(folder_in, "data_voxel.pck")
    filename_solution = os.path.join(folder_in, "data_solution.pck")

    # run and save the results
    run_save(filename_voxel, filename_solution, cfg_viewer, cfg_plotter, folder_out)

    # run the plotter (solver results)
    run_show(filename_voxel, filename_solution, cfg_viewer, cfg_plotter)

    # exit
    sys.exit(0)
