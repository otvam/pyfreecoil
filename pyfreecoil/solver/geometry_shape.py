"""
Geometry handling with shapely (with some bug workarounds).
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import warnings
import numpy as np
import shapely as sha

# remove shapely warnings
warnings.filterwarnings("ignore", module="shapely")
warnings.filterwarnings("ignore", module="numpy")


def _get_clean_shape(obj):
    """
    Clean a shape (or collections).
    Use multi-polygon as a general purpose output.
    Remove invalid/empty shapes.
    """

    # init
    obj_list = []

    # transform the shapes into meshes
    if isinstance(obj, sha.Polygon):
        if obj.is_valid and not obj.is_empty:
            obj_list.append(obj)
    elif isinstance(obj, sha.MultiPolygon):
        for obj_tmp in obj.geoms:
            if isinstance(obj_tmp, sha.Polygon):
                if obj_tmp.is_valid and not obj_tmp.is_empty:
                    obj_list.append(obj_tmp)
    elif isinstance(obj, sha.GeometryCollection):
        for obj_tmp in obj.geoms:
            if isinstance(obj_tmp, sha.Polygon):
                if obj_tmp.is_valid and not obj_tmp.is_empty:
                    obj_list.append(obj_tmp)
    else:
        raise ValueError("invalid shape type")

    # assemble
    obj = sha.MultiPolygon(obj_list)

    return obj


def get_trace(coord_1, coord_2, width_1, width_2):
    """
    Create a trace with variable width.
    The trace is smooth when terminated with round pads.
    """

    # get points
    (x_1, y_1) = coord_1
    (x_2, y_2) = coord_2
    r_1 = width_1/2
    r_2 = width_2/2

    # get direction vector
    d_x = x_2-x_1
    d_y = y_2-y_1

    # trace length
    dis = np.hypot(d_x, d_y)

    # check if the tangent exists
    valid = dis > np.abs(r_2 - r_1)

    # check if the tangent exists
    if valid:
        # normalize vector
        d_x = d_x/dis
        d_y = d_y/dis

        # segment angles and direction vector
        angle_1 = np.arctan2(d_y, d_x)
        angle_2 = np.arccos((r_1-r_2)/dis)

        # assemble the polygon coordinates
        coord = np.array([
            [x_1-d_x*r_1, y_1-d_y*r_1],
            [x_1+r_1*np.cos(angle_1+angle_2), y_1+r_1*np.sin(angle_1+angle_2)],
            [x_2+r_2*np.cos(angle_1+angle_2), y_2+r_2*np.sin(angle_1+angle_2)],
            [x_2+d_x*r_2, y_2+d_y*r_2],
            [x_2+r_2*np.cos(angle_1-angle_2), y_2+r_2*np.sin(angle_1-angle_2)],
            [x_1+r_1*np.cos(angle_1-angle_2), y_1+r_1*np.sin(angle_1-angle_2)],
        ], dtype=np.float64)
    else:
        coord = None

    # assemble
    shape = {"geom": "trace", "data": coord, "valid": valid}

    return shape


def get_pad(coord, diameter):
    """
    Create a round pad.
    """

    # get a point
    valid = diameter > 0.0

    # assemble
    shape = {"geom": "pad", "data": (coord, diameter), "valid": valid}

    return shape


def get_shape(shape_list):
    """
    Transform shapes into Shapely objects.
    """

    # list for the shape object
    obj_list = []

    # create the object
    for shape in shape_list:
        # extract
        geom = shape["geom"]
        data = shape["data"]
        valid = shape["valid"]

        # construct the shape
        if valid:
            # get the shape
            if geom == "trace":
                obj = sha.Polygon(data)
            elif geom == "pad":
                (coord, diameter) = data
                obj = sha.Point(coord).buffer(diameter/2, quadsegs=16)
            else:
                raise ValueError("invalid shape")

            # check data
            if not obj.is_valid:
                raise RuntimeError("invalid polygon")

            # append
            obj_list.append(obj)

    return obj_list


def get_polygon(coord, keepout):
    """
    Create a polygon from a coordinate list.
    """

    # get object
    obj = sha.Polygon(coord, holes=keepout)

    # check data
    if not obj.is_valid:
        raise RuntimeError("invalid polygon")

    return obj


def get_union(obj_list, construct):
    """
    Union between several shapes.
    Clean the resulting shape.
    """

    # merge the shape
    if len(obj_list) == 0:
        obj = sha.Polygon([])
    elif len(obj_list) == 1:
        obj = obj_list.pop()
    else:
        obj = sha.unary_union(obj_list, grid_size=construct)

    # clean the shape
    obj = _get_clean_shape(obj)

    return obj


def get_difference(add, sub, construct):
    """
    Difference between two shapes.
    Clean the resulting shape.
    """

    # intersect the shape
    if add.is_empty or sub.is_empty:
        obj = add
    else:
        obj = sha.difference(add, sub, grid_size=construct)

    # clean the shape
    obj = _get_clean_shape(obj)

    return obj


def get_simplify(obj, simplify):
    """
    Simplify a shape.
    Clean the resulting shape.
    """

    obj = obj.simplify(simplify, preserve_topology=False)
    obj = _get_clean_shape(obj)

    return obj
