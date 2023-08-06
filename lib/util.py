import prometheus_client as metrics

'''
    Helper to get a reference to a metric by name
'''
def get_metric(metric_name):
    if metric_name not in metrics.REGISTRY._names_to_collectors:
        return None

    return metrics.REGISTRY._names_to_collectors[metric_name]