from exporters import exporter
from lib import timing
import time

class DummyExporter(exporter.Exporter):
    job_name = 'DummyExporter'
    
    '''
        Dummy metric as an example
    '''
    def gather_metrics(self):
        dummy_gauge = self.metrics.Gauge('dummy_gauge', 'A dummy metric, means nothing.')
        dummy_counter = self.metrics.Counter('dummy_counter', 'A dummy metric, means nothing.', ['dummy_label'])

        # let's sleep a bit to simulate some work
        time.sleep(1)

        dummy_counter.labels('dummy_label_value').inc(1)

        self.observed_function()

    '''
        Helpers for tracking execution time of methods are provided,
        timing.observed decorator will automatically time and create a metric
        for the function it's decorating
    '''
    @timing.observed
    def observed_function(self):
        time.sleep(0.3)

        '''
            ...alternatively, anything can be manually timed with the timing.Observe
            context manager
        '''
        with timing.Observe(self, 'my_custom_task'):
            time.sleep(0.55)
        '''
            This automatically creates metrics similar to these:

            # HELP execution_seconds Summary of time spent executing something
            # TYPE execution_seconds summary
            execution_seconds_count{function="DummyExporter.my_custom_task"} 1.0
            execution_seconds_sum{function="DummyExporter.my_custom_task"} 0.551
            execution_seconds_count{function="DummyExporter.observed_function"} 1.0
            execution_seconds_sum{function="DummyExporter.observed_function"} 1.102
        '''

        '''
            If you'd like to time something but not turn it into a metric, there is also 
            a generic timer context manager
        '''
        with timing.Timer() as timer:
            time.sleep(0.25)

        dummy_counter = self.metrics.Counter('generic_timer_seconds', 'Value of generic timer')
        dummy_counter.inc(timer.value)
        '''
            # HELP generic_timer_seconds_total Value of generic timer
            # TYPE generic_timer_seconds_total counter
            generic_timer_seconds_total 0.25
        '''