"""
Module for checking the design rules.
Uses the "data_vector" shapes as an input.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np
import scipy.spatial as spa
import scipy.signal as sig
from pyfreecoil.solver import geometry_shape


def _get_segment(coord):
    """
    Get the segment lengths from a coordinate vector.
    """

    segment = np.diff(coord, 1, 0)
    segment = np.hypot(segment[:, 0], segment[:, 1])

    return segment


def _get_angle(coord):
    """
    Compute the segment angles from a coordinate vector.
    """

    # get segments
    segment = np.diff(coord, 1, 0)
    segment_1 = segment[:-1]
    segment_2 = segment[+1:]

    # get angle
    dot_1 = segment_1[:, 0]*segment_2[:, 1]-segment_1[:, 1]*segment_2[:, 0]
    dot_2 = segment_1[:, 0]*segment_2[:, 0]+segment_1[:, 1]*segment_2[:, 1]
    angle = np.arctan2(dot_1, dot_2)

    # get the sharp angle
    angle = np.abs(np.pi-np.abs(angle))

    # find singular angles
    eps = np.finfo(1.0).eps
    singular_1 = np.all(np.abs(segment_1) < eps, axis=1)
    singular_2 = np.all(np.abs(segment_2) < eps, axis=1)
    singular = np.logical_or(singular_1, singular_2)

    # handle singular angles
    angle[singular] = np.pi

    return angle


def _get_segment_resample(coord, width, size_min, dis_resample):
    """
    Resample a coordinate vector and a width vector.
    Compute the cumulative distance from the start.
    """

    # get segments
    seg_ref = _get_segment(coord)

    # get cumulative distance
    dis_ref = np.append(0.0, np.cumsum(seg_ref))

    # get the number of segments
    length = np.sum(seg_ref)
    n_segment = np.round(length/dis_resample)
    n_segment = np.maximum(size_min, n_segment+1)
    n_segment = int(n_segment)

    # resampled cumulative distance
    dis = np.linspace(0, length, n_segment)

    # interpolation of the coordinate and width
    width = np.interp(dis, dis_ref, width)
    x_pts = np.interp(dis, dis_ref, coord[:, 0])
    y_pts = np.interp(dis, dis_ref, coord[:, 1])
    coord = np.vstack((x_pts, y_pts)).transpose()

    return dis, coord, width


def _check_trace_distance_seg_sub(geom, distance_options):
    """
    Compute the internal distance within a trace.
    This is used to avoid "quasi-intersection" within a trace.

    Resample the trace into many segments.
    Compute the distance between all the points.
    Ignore the distance of the points that are close to each others.
    Return the minimum distance.
    """

    # extract
    coord = geom["coord"]
    width = geom["width"]

    # extract
    size_min = distance_options["size_min"]
    dis_resample = distance_options["dis_resample"]
    tol_angle = distance_options["tol_angle"]
    tol_add = distance_options["tol_add"]

    # resample the trace
    (dis, coord, width) = _get_segment_resample(coord, width, size_min, dis_resample)

    # compute the trace width
    (mat_a, mat_b) = np.meshgrid(width, width)
    mat_width = (mat_a+mat_b)/2

    # compute distance between all the points
    mat_pts = spa.distance.pdist(coord)
    mat_pts = spa.distance.squareform(mat_pts)

    # compute distance along the path
    dis = np.expand_dims(dis, axis=1)
    mat_seg = spa.distance.pdist(dis)
    mat_seg = spa.distance.squareform(mat_seg)

    # detect the points that are quasi-adjacent
    tol_angle = np.deg2rad(tol_angle)
    mag_len = mat_width/np.sin(tol_angle/2)
    mat_check = mat_seg < (tol_add+mag_len)

    # create the distance matrix
    mat_final = mat_pts-mat_width

    # ignore the distance of the points that are quasi-adjacent
    mat_final[mat_check] = np.PINF

    # get the critical distance
    distance = np.min(mat_final)

    return distance


def _check_trace_distance_end_sub(geom):
    """
    Compute the distance between the start/end nodes of a trace.
    """

    # extract
    coord = geom["coord"]
    width = geom["width"]

    # start and end node
    coord = coord[+0]-coord[-1]
    width = (width[+0]+width[-1])/2

    # node distance
    distance = np.hypot(coord[0], coord[1])-width

    return distance


def _check_trace_distance(geom_trace, distance_options):
    """
    Compute the clearance within a trace:
        - Compute the internal distance (detect quasi-intersection)
        - Compute the distance between the start/end nodes
    """

    # init
    distance = np.empty(0, dtype=np.float64)

    # get internal clearance
    for geom_tmp in geom_trace:
        distance_tmp = _check_trace_distance_seg_sub(geom_tmp, distance_options)
        distance = np.append(distance, distance_tmp)

    # get the start/end clearance
    for geom_tmp in geom_trace:
        distance_tmp = _check_trace_distance_end_sub(geom_tmp)
        distance = np.append(distance, distance_tmp)

    return distance


def _check_clearance_sub(geom_all, idx):
    """
    Compute the clearance between different shapes for a given layer.
    """

    # init a vector with all the shapes
    obj_list = []

    # assemble a vector with all the shapes
    for geom_tmp in geom_all:
        # extract
        layer = geom_tmp["layer"]
        obj = geom_tmp["obj"]

        # if invalid, clearance is negative infinity
        if not obj.is_valid:
            return np.NINF

        # append if the layer is matching
        if idx in layer:
            obj_list.append(obj)

    # if empty, clearance is positive infinity
    if len(obj_list) == 0:
        return np.PINF

    # init a matrix with the clearance between the shapes
    clearance_list = np.zeros((len(obj_list), len(obj_list)), dtype=np.float64)

    # compute the clearance distance matrix
    for idx, obj in enumerate(obj_list):
        clearance_list[idx] = obj.distance(obj_list)

    # remove the diagonal (self-clearance)
    np.fill_diagonal(clearance_list, np.PINF)

    # get the minimum clearance
    clearance = np.min(clearance_list)

    return clearance


def _check_clearance(geom_shape, geom_terminal, position):
    """
    Compute the clearance between different shapes for all the layers.
    """

    # init
    clearance = np.empty(0, dtype=np.float64)

    # get clearance for each layer
    for idx in range(len(position)):
        # compute the clearance between the shapes
        clearance_tmp = _check_clearance_sub(geom_shape, idx)
        clearance = np.append(clearance, clearance_tmp)

        # compute the clearance between the terminals
        clearance_tmp = _check_clearance_sub(geom_terminal, idx)
        clearance = np.append(clearance, clearance_tmp)

    return clearance


def _check_trace_base_sub(geom):
    """
    Compute basic properties of a trace:
        - Angles between the segments
        - Lengths of the segments
        - Widths of the trace
    """

    # extract
    coord = geom["coord"]
    width = geom["width"]

    # angle
    angle = _get_angle(coord)

    # get length
    segment = _get_segment(coord)
    length = np.sum(segment)

    return angle, length, width


def _check_trace_resample_sub(geom, average_options):
    """
    Compute advanced properties of a trace:
        - Compute the "locally averaged curvature rate"
        - Compute the "locally averaged width gradient"
    """

    # extract
    coord = geom["coord"]
    width = geom["width"]

    # extract
    size_min = average_options["size_min"]
    window_conv = average_options["window_conv"]
    length_min = average_options["length_min"]
    dis_resample = average_options["dis_resample"]
    dis_average = average_options["dis_average"]

    # resample the trace
    (dis, coord, width) = _get_segment_resample(coord, width, size_min, dis_resample)

    # short trace are valid as local parameters cannot be computed
    if np.max(dis) < length_min:
        return 0.0, 0.0

    # get the size of the moving average convolution filter
    sample = np.mean(np.diff(dis))
    repeat = int(np.round(dis_average/sample))

    # compute the width gradient
    diff = np.abs(np.diff(width))
    diff = diff/(repeat*sample)

    # compute the curvature rate
    radius = _get_angle(coord)
    radius = np.abs(np.pi-radius)

    # local average for the width gradient
    conv = np.minimum(repeat, len(diff))
    window = sig.windows.get_window(window_conv, conv)
    diff = np.convolve(diff, window, mode="valid")
    diff = np.max(diff)

    # local average for the curvature rate
    conv = np.minimum(repeat, len(radius))
    window = sig.windows.get_window(window_conv, conv)
    radius = np.convolve(radius, window, mode="valid")
    radius = np.max(radius)

    return diff, radius


def _check_trace_base(geom_trace):
    """
    Compute basic properties for all the traces:
    """

    # init
    angle = np.empty(0, dtype=np.float64)
    length = np.empty(0, dtype=np.float64)
    width = np.empty(0, dtype=np.float64)

    # get the properties
    for geom_tmp in geom_trace:
        (angle_tmp, length_tmp, width_tmp) = _check_trace_base_sub(geom_tmp)
        angle = np.append(angle, angle_tmp)
        length = np.append(length, length_tmp)
        width = np.append(width, width_tmp)

    return angle, length, width


def _check_trace_resample(geom_trace, average_options):
    """
    Compute advanced properties for all the traces:
    """

    # init
    diff = np.empty(0, dtype=np.float64)
    radius = np.empty(0, dtype=np.float64)

    # get the properties
    for geom_tmp in geom_trace:
        (diff_tmp, radius_tmp) = _check_trace_resample_sub(geom_tmp, average_options)
        diff = np.append(diff, diff_tmp)
        radius = np.append(radius, radius_tmp)

    return diff, radius


def _check_box(geom_all, outline, keepout, simplify, construct):
    """
    Compute the distance between the shapes and the outline.
    """

    # init a vector with all the shapes
    obj_list = []

    # assemble a vector with all the shapes
    for geom_tmp in geom_all:
        # extract
        obj = geom_tmp["mask"]

        # if invalid, clearance is positive infinity
        if not obj.is_valid:
            return np.PINF

        # append the shape
        obj_list.append(obj)

    # if empty, clearance is negative infinity
    if len(obj_list) == 0:
        return np.NINF

    # merge and simplify the shapes
    obj = geometry_shape.get_union(obj_list, construct)
    obj = geometry_shape.get_simplify(obj, simplify)

    # get a polygon mask from the outline
    outline = geometry_shape.get_polygon(outline, keepout)

    # check the distance between the shapes and the outline
    if outline.contains(obj):
        # if the shapes are inside the outline, return the distance (negative sign)
        boundary = obj.distance(outline.boundary)
        boundary = np.negative(boundary)
    else:
        # if the shapes are outside the outline, return the overlap (positive sign)
        obj_tmp = geometry_shape.get_difference(obj, outline, construct)
        obj_tmp = geometry_shape.get_simplify(obj_tmp, simplify)
        boundary = np.sqrt(obj_tmp.area)

    return boundary


def _check_bnd_range(valid_clamp, val, limit):
    """
    Check if a variable lies between two bounds.
    Return a (scaled) validity parameters (negative for valid).
    """

    # extract the clip values
    bnd_min = valid_clamp["bnd_min"]
    bnd_max = valid_clamp["bnd_max"]

    # get the limits
    (v_min, v_max) = limit

    # get all the values as a flat array
    val = np.array([val], dtype=np.float64)
    val = val.flatten()

    # init with valid values (negative infinity)
    rel_min = np.NINF
    rel_max = np.NINF

    # compute the relative error with the bounds
    if len(val) > 0:
        if v_min is not None:
            rel_min = (v_min-np.min(val))/v_min
        if v_max is not None:
            rel_max = (np.max(val)-v_max)/v_max

    # select the worst case between both bounds
    rel = np.maximum(rel_min, rel_max)

    # clip the value
    rel = np.clip(rel, bnd_min, bnd_max)

    return rel


def _check_bnd_single(valid_clamp, val, limit):
    """
    Check that a variable is negative.
    Return a (scaled) validity parameters (negative for valid).
    """

    # extract the clip values
    bnd_min = valid_clamp["bnd_min"]
    bnd_max = valid_clamp["bnd_max"]

    # init with a valid value (negative infinity)
    rel = np.NINF

    # scale the variable
    if limit is not None:
        rel = val/limit

    # clip the value
    rel = np.clip(rel, bnd_min, bnd_max)

    return rel


def run_check(data_vector, shapely, design_rule):
    """
    Check the complete design rules.
    Uses the "data_vector" shapes as an input.

    The validity is evaluated with a float variables:
        - Negative values are respecting constraints
        - Positive values are violating constraints
    """

    # extract
    limit_val = design_rule["limit_val"]
    valid_clamp = design_rule["valid_clamp"]
    average_options = design_rule["average_options"]
    distance_options = design_rule["distance_options"]

    # extract
    simplify = shapely["simplify"]
    construct = shapely["construct"]

    # extract
    position = data_vector["position"]
    outline = data_vector["outline"]
    keepout = data_vector["keepout"]
    geom_via = data_vector["geom_via"]
    geom_trace = data_vector["geom_trace"]
    geom_src = data_vector["geom_src"]
    geom_sink = data_vector["geom_sink"]

    # combines the different shapes
    geom_terminal = [geom_src, geom_sink]
    geom_shape = geom_via+geom_trace
    geom_all = geom_shape+geom_terminal

    # compute the distance between the shapes and the
    boundary = _check_box(geom_all, outline, keepout, simplify, construct)

    # compute the clearance between different shapes for all the layers
    clearance = _check_clearance(geom_shape, geom_terminal, position)

    # compute the parameters of the different traces
    (angle, length, width) = _check_trace_base(geom_trace)
    (diff, radius) = _check_trace_resample(geom_trace, average_options)
    distance = _check_trace_distance(geom_trace, distance_options)

    # cast angles to degree
    angle = np.rad2deg(angle)
    radius = np.rad2deg(radius)

    # compute the scaled validity parameters
    valid_boundary = _check_bnd_single(valid_clamp, boundary, limit_val["boundary"])
    valid_clearance = _check_bnd_range(valid_clamp, clearance, limit_val["clearance"])
    valid_length = _check_bnd_range(valid_clamp, length, limit_val["length"])
    valid_distance = _check_bnd_range(valid_clamp, distance, limit_val["distance"])
    valid_width = _check_bnd_range(valid_clamp, width, limit_val["width"])
    valid_angle = _check_bnd_range(valid_clamp, angle, limit_val["angle"])
    valid_diff = _check_bnd_range(valid_clamp, diff, limit_val["diff"])
    valid_radius = _check_bnd_range(valid_clamp, radius, limit_val["radius"])

    # assign
    data_valid = {
        "valid_boundary": valid_boundary,
        "valid_clearance": valid_clearance,
        "valid_length": valid_length,
        "valid_distance": valid_distance,
        "valid_width": valid_width,
        "valid_angle": valid_angle,
        "valid_diff": valid_diff,
        "valid_radius": valid_radius,
    }

    return data_valid
