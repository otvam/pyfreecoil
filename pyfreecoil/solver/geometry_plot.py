"""
Module for plotting the inductor geometry (2D plots).
Uses the "data_vector" shapes as an input.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import matplotlib.pyplot as plt
import shapely.plotting as shp
import shapely.affinity as sht
import shapely as sha
import numpy as np
import warnings

# remove shapely warnings
warnings.filterwarnings("ignore", module="shapely")
warnings.filterwarnings("ignore", module="numpy")


def _extract_geom(data_vector):
    """
    Extract the different shapes composing a design.
    """

    # extract data
    geom_via = data_vector["geom_via"]
    geom_trace = data_vector["geom_trace"]
    geom_src = data_vector["geom_src"]
    geom_sink = data_vector["geom_sink"]
    outline = data_vector["outline"]
    keepout = data_vector["keepout"]

    # outline to polygon
    outline = sha.Polygon(outline, holes=keepout)

    # merge src and sink
    geom_terminal = [geom_src, geom_sink]

    return outline, geom_via, geom_trace, geom_terminal


def _merge_material(geom_via, geom_trace, geom_terminal):
    """
    Merge all the shapes together (conductors and terminals).
    """

    # merge geometries
    terminal_list = [item["obj"] for item in geom_terminal]
    trace_list = [item["obj"] for item in geom_trace]
    via_list = [item["obj"] for item in geom_via]

    # assemble the data
    terminal = sha.unary_union(terminal_list)
    conductor = sha.unary_union(trace_list+via_list)

    return conductor, terminal


def _merge_mask(geom_via, geom_trace, geom_terminal):
    """
    Merge all the shapes together (shapes and masks).
    """

    # add shapes
    geom_all = geom_via+geom_trace+geom_terminal

    # init
    obj_list = [item["obj"] for item in geom_all]
    mask_list = [item["mask"] for item in geom_all]

    # assemble the data
    obj = sha.unary_union(obj_list)
    mask = sha.unary_union(mask_list)

    return obj, mask


def _merge_trace(geom_trace, select):
    """
    Merge all the traces for a given layer.
    """

    # init list containing the traces
    coord_list = []

    # init the traces with the right layer
    for geom_tmp in geom_trace:
        coord = geom_tmp["coord"]
        layer = geom_tmp["layer"]
        for select_tmp in select:
            if np.array_equal(layer, select_tmp):
                coord_list.append(coord)

    # assemble the data
    obj = sha.MultiLineString(coord_list)

    return obj


def _merge_layer(geom_via, geom_trace, geom_terminal, select):
    """
    Merge all the shapes for a given layer.
    """

    # combine shapes
    geom_all = geom_via+geom_trace+geom_terminal

    # init list containing the shapes
    obj_list = []

    # init the shapes with the right layer
    for geom_tmp in geom_all:
        obj = geom_tmp["obj"]
        layer = geom_tmp["layer"]
        for select_tmp in select:
            if np.array_equal(layer, select_tmp):
                obj_list.append(obj)

    # assemble the data
    obj = sha.unary_union(obj_list)

    return obj


def _plot_polygon(obj, scl_shape, param):
    """
    Plot a polygon (or polygons).
    """

    # scale unit
    obj = sht.scale(obj, scl_shape, scl_shape, scl_shape, origin=(0.0, 0.0, 0.0))

    # plot polygon
    if obj.is_valid and not obj.is_empty:
        shp.plot_polygon(
            obj, add_points=False,
            facecolor=param["face"],
            edgecolor=param["edge"],
            linewidth=param["line"],
        )


def _plot_line(obj, scl_shape, param):
    """
    Plot a line (or lines).
    """

    # scale unit
    obj = sht.scale(obj, scl_shape, scl_shape, scl_shape, origin=(0.0, 0.0, 0.0))

    # plot polygon
    if obj.is_valid and not obj.is_empty:
        shp.plot_line(
            obj, add_points=True,
            color=param["color"],
            linewidth=param["width"],
        )


def run_shape(data_vector, param_shared, data_shaper):
    """
    Plot the geometry outline, the different shapes, and layers.
    """

    # extract
    layer_def = data_shaper["layer_def"]
    shape_color = data_shaper["shape_color"]
    line_color = data_shaper["line_color"]

    # extract
    scl_shape = param_shared["scl_shape"]
    color_outline = param_shared["color_outline"]

    # merge geometries
    (outline, geom_via, geom_trace, geom_terminal) = _extract_geom(data_vector)

    # plot figure
    plt.figure()
    _plot_polygon(outline, scl_shape, color_outline)
    for name, select in layer_def.items():
        obj = _merge_layer(geom_via, geom_trace, geom_terminal, select)
        _plot_polygon(obj, scl_shape, shape_color[name])
    for name, select in layer_def.items():
        obj = _merge_trace(geom_trace, select)
        _plot_line(obj, scl_shape, line_color[name])

    plt.grid(False)
    plt.axis("equal")
    plt.title("Outline and Shapes")
    plt.tight_layout()
    plt.axis("off")


def run_mask(data_vector, param_shared, param_mask):
    """
    Plot the geometry outline, the shapes, and the masks.
    """

    # extract
    color_obj = param_mask["color_obj"]
    color_mask = param_mask["color_mask"]

    # extract
    scl_shape = param_shared["scl_shape"]
    color_outline = param_shared["color_outline"]

    # merge geometries
    (outline, geom_via, geom_trace, geom_terminal) = _extract_geom(data_vector)
    (obj, mask) = _merge_mask(geom_via, geom_trace, geom_terminal)

    # plot figure
    plt.figure()
    _plot_polygon(outline, scl_shape, color_outline)
    _plot_polygon(obj, scl_shape, color_obj)
    _plot_polygon(mask, scl_shape, color_mask)
    plt.grid(False)
    plt.axis("equal")
    plt.title("Outline, Shapes, Masks")
    plt.tight_layout()
    plt.axis("off")


def run_terminal(data_vector, param_shared, param_material):
    """
    Plot the geometry outline, the conductors, and the terminals.
    """

    # extract
    color_conductor = param_material["color_conductor"]
    color_terminal = param_material["color_terminal"]

    # extract
    scl_shape = param_shared["scl_shape"]
    color_outline = param_shared["color_outline"]

    # merge geometries
    (outline, geom_via, geom_trace, geom_terminal) = _extract_geom(data_vector)
    (conductor, terminal) = _merge_material(geom_via, geom_trace, geom_terminal)

    # plot figure
    plt.figure()
    _plot_polygon(outline, scl_shape, color_outline)
    _plot_polygon(conductor, scl_shape, color_conductor)
    _plot_polygon(terminal, scl_shape, color_terminal)
    plt.grid(False)
    plt.axis("equal")
    plt.title("Outline, Conductors, and Terminals")
    plt.tight_layout()
    plt.axis("off")
