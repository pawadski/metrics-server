import os
import sys

'''
    Base exporter class, all exporters must inherit this class.

    It is recommended to keep all data gathering functionality inside gather_metrics
    as an entry point. The base class will handle everything else.

    Static properties: 
        job_name - used to group metrics under a specific job label
                   when pushing to Pushgateway
           debug - commandline --debug flag

    See dummy.py
'''
class Exporter:
    job_name = 'exporter'
    debug = False

    def __init__(self, prometheus_client, debug, *args):
        self.metrics = prometheus_client
        self.debug = debug
        self.args = self.parse_args(*args)

    '''
        You can handle all argument parsing here
    '''
    def parse_args(self, *args):
        pass

    '''
        This is the entry point, override it with any custom logic

        prometheus_client module is available via self.metrics
        all unknown arguments passed to metrics are available via self.args
    '''
    def gather_metrics(self):
        pass

    '''
        If you want to use asyncio, defining gather_metrics as a coroutine
        is supported, ie. async def gather_metrics(self)...
    '''