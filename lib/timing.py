import time 
import functools
import contextlib
import prometheus_client as metrics
from lib import util

def _get_or_create_metric():
    metric = util.get_metric("execution_seconds")
    if metric is None:
        metric = metrics.Summary("execution_seconds", "Summary of time spent executing something", ['function'])

    return metric

def observed(method):
    summary = _get_or_create_metric()

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        start = time.perf_counter()
        result = method(self, *args, **kwargs)
        summary.labels(f"{self.__class__.__name__}.{method.__name__}").observe(round(time.perf_counter() - start, 3))

        return result
    return wrapper

class Observe():
    def __init__(self, class_ref, name):
        self.name = f"{class_ref.__class__.__name__}.{name}"
        self.summary = _get_or_create_metric()
    
    def __enter__(self):
        self.start = time.perf_counter()

    def __exit__(self, *args):
        self.summary.labels(self.name).observe(round(time.perf_counter() - self.start, 3))

'''
    Generic timer, no metrics
'''
class Timer():
    def __init__(self):
        pass
    
    def __enter__(self):
        self.start = time.perf_counter()

        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.value = round(self.end - self.start, 3)

    def __repr__(self):
        return self.value