"""
Export a planar inductor geometry to GERBER files.
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
import scisave
import scilogger
import numpy as np
from gerber_writer import DataLayer
from gerber_writer import Circle
from gerber_writer import UserPolygon

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def _get_gerber_pad(gerber, name, data, options):
    """
    Create GERBER circle for a circular pad.
    """

    # get options
    scaling = options["scaling"]
    offset_x = options["offset_x"]
    offset_y = options["offset_y"]

    # extract and copy
    (coord, diameter) = data
    coord = coord.copy()
    diameter = diameter.copy()

    # scaling and offset
    diameter = scaling*diameter
    coord[0] = scaling*(coord[0]+offset_x)
    coord[1] = scaling*(coord[1]+offset_y)

    # create and add GERBER circle
    pad = Circle(diameter, name)
    gerber.add_pad(pad, tuple(coord))


def _get_gerber_trace(gerber, name, data, options):
    """
    Create GERBER circle for a trace segment.
    """

    # get options
    scaling = options["scaling"]
    offset_x = options["offset_x"]
    offset_y = options["offset_y"]

    # extract and copy
    data = data.copy()

    # scaling and offset
    data[:, 0] = scaling*(data[:, 0]+offset_x)
    data[:, 1] = scaling*(data[:, 1]+offset_y)

    # close the polygon
    data = np.vstack((data, data[0]))

    # create and add GERBER trace
    poly = UserPolygon(tuple(map(tuple, data)), name)
    gerber.add_pad(poly, (0.0, 0.0))


def _get_gerber_shape(gerber, name, shape, options):
    """
    Add a single shape to the GERBER data.
    """

    # extract
    geom = shape["geom"]
    data = shape["data"]
    valid = shape["valid"]

    # construct the shape
    if valid:
        if geom == "trace":
            _get_gerber_trace(gerber, name, data, options)
        elif geom == "pad":
            _get_gerber_pad(gerber, name, data, options)
        else:
            raise ValueError("invalid shape")


def _get_gerber_geometry(gerber, count, tag, layer, cad, options, select):
    """
    Add a geometry to the GERBER data (for a specific layer).
    """

    for select_tmp in select:
        if np.array_equal(layer, select_tmp):
            for shape in cad:
                # get name
                name = "shape_%s_%d" % (tag, count)

                # update naming counter
                count += 1

                # add content
                _get_gerber_shape(gerber, name, shape, options)

    return count


def _get_gerber_layer(tag, geom_trace, geom_via, options, select):
    """
    Create a complete GERBER layer.
    """

    # create GERBER layer
    gerber = DataLayer(tag)

    # counter for naming
    count = 1

    # populate trace in the layer
    for geom in geom_trace:
        # extract
        layer = geom["layer"]
        cad = geom["cad_add"]

        # add data
        count = _get_gerber_geometry(gerber, count, tag, layer, cad, options, select)

    # populate vias in the layer
    for geom in geom_via:
        # extract
        layer = geom["layer"]
        cad = geom["cad_sub"]

        # add data
        count = _get_gerber_geometry(gerber, count, tag, layer, cad, options, select)

    return gerber


def get_gerber(data_vector, stack_dict, options):
    """
    Export a planar inductor geometry to GERBER layers.
    """

    # parse the geometry
    geom_trace = data_vector["geom_trace"]
    geom_via = data_vector["geom_via"]

    # dictionary containing the created layers
    gerber_dict = {}

    # create the GERBER files for the different layers
    LOGGER.info("parse gerber")
    with LOGGER.BlockIndent():
        for tag, select in stack_dict.items():
            LOGGER.info("parse gerber: %s" % tag)
            gerber_dict[tag] = _get_gerber_layer(tag, geom_trace, geom_via, options, select)

    return gerber_dict


def write_gerber(folder, gerber_dict):
    """
    Export GERBER layers to GERBER files.
    """

    # folder
    os.makedirs(folder, exist_ok=True)

    # write the STL files
    LOGGER.info("write gerber")
    with LOGGER.BlockIndent():
        for tag, data in gerber_dict.items():
            LOGGER.info("write gerber: %s" % tag)
            filename = os.path.join(folder, "%s.gbr" % tag)
            if len(data) > 0:
                with open(filename, "w") as fid:
                    data.dump_gerber(fid)


if __name__ == "__main__":
    # get the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_in", required=True, type=str, help="folder with the evaluated design")
    parser.add_argument("--folder_out", required=True, type=str, help="folder for the results (to be created)")
    parser.add_argument("--cfg_gerber", required=True, type=str, help="configuration file for the export")

    # parse arguments
    args = parser.parse_args()
    folder_in = args.folder_in
    folder_out = args.folder_out
    cfg_gerber = args.cfg_gerber

    # create the output folder
    os.makedirs(folder_out, exist_ok=True)

    # load the data containing the coil geometry
    data_vector = scisave.load_data(os.path.join(folder_in, "data_vector.pck"))

    # load the configuration data
    cfg_gerber = scisave.load_config(cfg_gerber)
    options = cfg_gerber["options"]
    stack_dict = cfg_gerber["stack_dict"]

    # get the GERBER layers
    gerber_dict = get_gerber(data_vector, stack_dict, options)

    # save GERBER files
    write_gerber(folder_out, gerber_dict)

    # exit
    sys.exit(0)
