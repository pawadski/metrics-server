import prometheus_client as metrics
from lib import timing
import time

'''
    Generic DataSource class that handles generating metrics for its own status
    and timing its own functions
'''
class DataSource:
    def __init__(self):
        pass