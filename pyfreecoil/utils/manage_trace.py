"""
Module for producing traceback dump files with a decorators.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import os
import random
import pickle
import importlib

# global variable for controlling trace generation
TRACE = True


class RandomGeometryError(RuntimeError):
    """
    Exception for signaling an exception handled with a traceback.
    """

    pass


def trace_reproduce(module, function, args):
    """
    Reproduce a traceback failure.
    """

    # global used to temporarily disable tracing
    global TRACE

    # dynamic import
    module = importlib.import_module(module)
    function = getattr(module, function)

    # disable traceback (to avoid the generation of a new trace file)
    TRACE = False

    # call the function
    try:
        function(*args)
    except Exception as ex:
        raise ex
    finally:
        TRACE = True


def trace_error(tag, function, args, ex):
    """
    Run the decorated function, catch exception, write traceback file, and reraise.
    """

    # if traceback is disabled, show the failure
    if not TRACE:
        raise ex

    # trace folder storage
    folder = "trace"

    # get a unique traceback filename
    filename = "trace_%s_%08x.pck" % (tag, random.getrandbits(32))

    # gather trace data
    data = {
        "tag": tag,
        "function": function.__name__,
        "module": function.__module__,
        "args": args,
        "ex": ex,
    }

    # write the traceback file
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, filename), "wb") as fid:
        pickle.dump(data, fid)
