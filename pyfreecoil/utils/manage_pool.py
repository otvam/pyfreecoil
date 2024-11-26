"""
Module for running tasks in parallel (multiprocessing):
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import multiprocessing
import threading
import time

# function to be called
FCT_COMPUTE = None


def _fct_call_pool(args):
    """
    Call the user specified function and return the results (used by FctPool and QueuePool).
    """

    return FCT_COMPUTE(*args)


def _fct_init_pool(fct_compute):
    """
    Assign the function for each process (used and FctPool).
    Call during the initialization of the process pool.
    """

    # get global
    global FCT_COMPUTE

    # assign global
    FCT_COMPUTE = fct_compute


class _ThreadException(threading.Thread):
    """
    Thread loop collecting the results from the queue (used by QueuePool).
    Collect the results and call the user provided collect function.
    Flag exception into a class property.
    """

    def __init__(self, n_total, call_iter, delay_collect, delay_timeout, fct_collect):
        # assign values
        self.n_total = n_total
        self.call_iter = call_iter
        self.delay_collect = delay_collect
        self.delay_timeout = delay_timeout
        self.fct_collect = fct_collect

        # contain eventual exceptions
        self.ex = None

        # superclass constructor
        super().__init__()

    def loop(self):
        # init collection data
        n_count = 0
        out_list = []
        timestamp = time.time()

        # collect immediately after starting
        self.fct_collect(out_list, n_count, self.n_total)

        # collect the results when available
        while True:
            # get the data from the queue
            try:
                out = self.call_iter.next(self.delay_timeout)
                out_list.append(out)
                n_count += 1
            except multiprocessing.TimeoutError:
                pass
            except StopIteration:
                break

            # collect is required
            delay_now = time.time() - timestamp
            if delay_now > self.delay_collect:
                self.fct_collect(out_list, n_count, self.n_total)
                timestamp = time.time()
                out_list = []

        # collect all remaining results
        self.fct_collect(out_list, n_count, self.n_total)

    def run(self):
        try:
            self.loop()
        except Exception as ex:
            self.ex = ex


class QueuePool:
    """
    Call a function is parallel with a process pool and a collect thread:
        - Vectorized multiprocessing call (imap function).
        - A thread is collecting the results when available.
    """

    def __init__(self, n_parallel, delay_collect, delay_timeout, fct_collect, fct_compute):
        """
        Constructor.
        Store the evaluation function.
        Create the process pool and the queue.
        """

        # assign
        self.n_parallel = n_parallel
        self.delay_collect = delay_collect
        self.delay_timeout = delay_timeout
        self.fct_compute = fct_compute
        self.fct_collect = fct_collect

        # create and init pool and queue
        if self.n_parallel == 0:
            self.pool_obj = None
        else:
            self.pool_obj = multiprocessing.Pool(n_parallel, _fct_init_pool, [self.fct_compute])

    def _get_map_parallel(self, *args):
        """
        Vectorized multiprocessing call (imap function).
        A thread is collecting the results when available.
        """

        # count data
        n_total = len(list(zip(*args)))

        # run in parallel
        call_iter = self.pool_obj.imap_unordered(_fct_call_pool, zip(*args), chunksize=1)

        # start collecting thread
        thread = _ThreadException(n_total, call_iter, self.delay_collect, self.delay_timeout, self.fct_collect)
        thread.start()
        thread.join()

        # reraise thread exceptions
        if thread.ex is not None:
            raise thread.ex

    def _get_map_serial(self, *args):
        """
        Vectorized call (without parallel processing).
        """

        # count data
        n_total = len(list(zip(*args)))

        # init counter
        n_count = 0

        # run sequentially and collect immediately
        for args_tmp in zip(*args):
            n_count += 1
            out = self.fct_compute(*args_tmp)
            self.fct_collect([out], n_count, n_total)

    def get_loop(self, *args):
        """
        Vectorized call with result collector.
        """

        if self.n_parallel == 0:
            self._get_map_serial(*args)
        else:
            self._get_map_parallel(*args)

    def close(self):
        """
        Close the process pool and the queue.
        """

        if self.n_parallel != 0:
            self.pool_obj.close()


class FctPool:
    """
    Call a function is parallel with a process pool:
        - Parallel blocking call (apply function).
        - Vectorized blocking call (imap function).
    """

    def __init__(self, n_parallel, fct_compute):
        """
        Constructor.
        Store the evaluation function.
        Create the process pool.
        """

        # assign
        self.n_parallel = n_parallel
        self.fct_compute = fct_compute

        # create and init pool
        if self.n_parallel == 0:
            self.pool_obj = None
        else:
            self.pool_obj = multiprocessing.Pool(n_parallel, _fct_init_pool, [self.fct_compute])

    def get_fct(self, *args):
        """
        Parallel blocking call.
        """

        if self.n_parallel == 0:
            out = self.fct_compute(*args)
        else:
            out = self.pool_obj.apply(_fct_call_pool, [args])

        return out

    def get_loop(self, *args):
        """
        Vectorized blocking call.
        """

        if self.n_parallel == 0:
            out = [self.fct_compute(*args_tmp) for args_tmp in zip(*args)]
        else:
            out = self.pool_obj.imap(_fct_call_pool, zip(*args), chunksize=1)
            out = list(out)

        return out

    def close(self):
        """
        Close the process pool.
        """

        if self.n_parallel != 0:
            self.pool_obj.close()
