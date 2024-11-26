"""
Export a planar inductor geometry to STL/STEP files.
The input file (data_vector structure) contains the inductor geometry:
    - object shapes (traces and vias)
    - layer information
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import os
import sys
import argparse
import tempfile
import scisave
import scilogger
import numpy as np
import pyvista as pv
import cadquery as cq

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def _get_cad_shape(cad, shape, scaling):
    """
    Construct a 2D CAD object.
    """

    # extract
    geom = shape["geom"]
    data = shape["data"]
    valid = shape["valid"]

    # construct the shape
    if valid:
        if geom == "trace":
            data = scaling*data.copy()
            cad = cad.polyline(data)
            cad = cad.close()
        elif geom == "pad":
            (coord, diameter) = data
            coord = scaling*coord.copy()
            diameter = scaling*diameter.copy()
            cad = cad.moveTo(coord[0], coord[1])
            cad.circle(diameter/2)
        else:
            raise ValueError("invalid shape")

    return cad


def _get_cad_object(cad_add, cad_sub, z_min, z_max, scaling):
    """
    Construct a 3D CAD object.
    """

    # create shape
    cad = cq.Workplane("XY", origin=(0.0, 0.0, scaling*z_min))

    # add the shapes
    for shape in cad_add:
        cad = _get_cad_shape(cad, shape, scaling)
        cad = cad.extrude(scaling*(z_max-z_min))

    # subtract the shapes
    for shape in cad_sub:
        cad = _get_cad_shape(cad, shape, scaling)
        cad = cad.cutThruAll()

    return cad


def _get_cad_layer(geom, position, scaling, select):
    """
    Get the CAD objects located in the specified layers.
    """

    # extract
    layer = geom["layer"]
    cad_add = geom["cad_add"]
    cad_sub = geom["cad_sub"]

    # list for storing the CAD objects
    cad_list = []

    # get the shapes
    for select_tmp in select:
        if np.array_equal(layer, select_tmp):
            # get absolute stack position
            z_vec = np.append(0.0, np.cumsum(position))-np.sum(position)/2

            # get stack position for the given layer
            z_min = z_vec[np.min(select_tmp)+0]
            z_max = z_vec[np.max(select_tmp)+1]

            # create the CAD object
            cad_list.append(_get_cad_object(cad_add, cad_sub, z_min, z_max, scaling))

    return cad_list


def _get_cad_merge(cad_list):
    """
    Compute the union between several CAD objects.
    """

    # create a union
    if len(cad_list) == 0:
        cad = None
    else:
        cad = cq.Workplane("XY")
        for cad_tmp in cad_list:
            cad = cad.union(cad_tmp)

    return cad


def get_cad(data_vector, stack_dict, scaling):
    """
    Export a planar inductor geometry to CAD objects.
    """

    # parse geometry
    position = data_vector["position"]
    geom_via = data_vector["geom_via"]
    geom_trace = data_vector["geom_trace"]
    geom_all = geom_via+geom_trace

    # dictionary containing the created CAD objects
    cad_dict = {}

    # create the CAD objects for the different layers
    LOGGER.info("parse object")
    with LOGGER.BlockIndent():
        for tag, select in stack_dict.items():
            LOGGER.info("parse object: %s" % tag)

            # create list for the CAD objects
            cad_list = []

            # create the CAD objects
            for geom in geom_all:
                cad_list += _get_cad_layer(geom, position, scaling, select)

            # add data
            cad_dict[tag] = _get_cad_merge(cad_list)

    return cad_dict


def write_cad(folder, cad_dict, tolerance):
    """
    Export CAD objects to STL/STEP files.
    """

    # folder
    os.makedirs(folder, exist_ok=True)

    # write the STL/STEP files
    LOGGER.info("write object")
    with LOGGER.BlockIndent():
        for tag, cad in cad_dict.items():
            LOGGER.info("write object: %s" % tag)

            # get the filenames
            filename_stl = os.path.join(folder, "%s.stl" % tag)
            filename_step = os.path.join(folder, "%s.step" % tag)

            # write the files
            if cad is not None:
                cad.val().exportStl(filename_stl, tolerance=tolerance)
                cad.val().exportStep(filename_step)


def get_mesh(cad_dict, tolerance):
    """
    Convert CAD objects to PyVista meshes.
    """

    # dictionary containing the created meshes
    mesh_dict = {}

    # convert the CAD objects into PyVista meshes
    LOGGER.info("mesh object")
    with LOGGER.BlockIndent():
        for tag, cad in cad_dict.items():
            LOGGER.info("mesh object: %s" % tag)

            # export a mesh and load it in PyVista
            if cad is not None:
                (_, filename) = tempfile.mkstemp(suffix=".stl")
                cad.val().exportStl(filename, tolerance=tolerance)
                mesh = pv.read(filename)
                os.remove(filename)
            else:
                mesh = pv.PolyData()

            # add data
            mesh_dict[tag] = mesh

    return mesh_dict


def plot_cad(mesh_dict, plot_dict):
    """
    Plot the 3D objects with PyVista.
    """

    # create a plotter
    pl = pv.Plotter()

    # add the 3D objects
    LOGGER.info("plot object")
    with LOGGER.BlockIndent():
        for tag in set(mesh_dict.keys()) & set(plot_dict.keys()):
            LOGGER.info("plot object: %s" % tag)

            # extract
            mesh = mesh_dict[tag]
            plot = plot_dict[tag]

            # add the mesh to PyVista
            if mesh.n_cells > 0:
                pl.add_mesh(mesh, **plot)

    # show the results
    pl.show()


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_in", required=True, type=str, help="folder with the evaluated design")
    parser.add_argument("--folder_out", required=True, type=str, help="folder for the results (to be created)")
    parser.add_argument("--cfg_cad", required=True, type=str, help="configuration file for the export")

    # parse arguments
    args = parser.parse_args()
    folder_in = args.folder_in
    folder_out = args.folder_out
    cfg_cad = args.cfg_cad

    # create the output folder
    os.makedirs(folder_out, exist_ok=True)

    # load the data containing the coil shapes
    data_vector = scisave.load_data(os.path.join(folder_in, "data_vector.pck"))

    # load the configuration data
    cfg_gerber = scisave.load_config(cfg_cad)
    scaling = cfg_gerber["scaling"]
    tolerance = cfg_gerber["tolerance"]
    stack_dict = cfg_gerber["stack_dict"]

    # get the CAD objects
    cad_dict = get_cad(data_vector, stack_dict, scaling)

    # save STL/STEP files
    write_cad(folder_out, cad_dict, tolerance)

    # plot options (passed to PyVista/add_mesh)
    plot_dict = {
        "bot": {"color": "orange", "style": "surface"},
        "top": {"color": "orange", "style": "surface"},
        "mid": {"color": "orange", "style": "surface"},
        "via": {"color": "orangered", "style": "surface"},
    }

    # show the 3D objects
    mesh_dict = get_mesh(cad_dict, tolerance)
    plot_cad(mesh_dict, plot_dict)

    # exit
    sys.exit(0)
