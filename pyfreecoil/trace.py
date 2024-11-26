"""
Module for loading a traceback file and reproducing the failure.
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import scisave
import scilogger
from pyfreecoil.utils import manage_trace

# get logger
LOGGER = scilogger.get_logger(__name__, "planar")


def get_run(filename):
    """
    Load a traceback file and reproduce the failure.
    """

    # load data
    data = scisave.load_data(filename)
    name = getattr(filename, "stem")

    LOGGER.info("====================== START: %s" % name)

    # extract traceback
    tag = data["tag"]
    function = data["function"]
    module = data["module"]
    args = data["args"]
    ex = data["ex"]

    # show traceback info
    LOGGER.info("information")
    with LOGGER.BlockIndent():
        LOGGER.info("tag : %s" % tag)
        LOGGER.info("function : %s" % function)
        LOGGER.info("module : %s" % module)
    LOGGER.info("exception")
    with LOGGER.BlockIndent():
        LOGGER.log_exception(ex, level="INFO")

    # reproduce the failure
    LOGGER.info("reproduce")
    with LOGGER.BlockIndent():
        # mark the start of the call
        LOGGER.info("call start")

        # call and display the failure
        try:
            manage_trace.trace_reproduce(module, function, args)
        except Exception as ex:
            LOGGER.log_exception(ex, level="INFO")

        # mark the end of the call
        LOGGER.info("call end")

    LOGGER.info("====================== END: %s" % name)
