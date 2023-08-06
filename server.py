from sanic import Sanic, text, json
import os
import time
import asyncio
import re
from multiprocessing import Manager
from aiopipe import aiopipe

class Environment:
    WORKERS = int(os.getenv('WORKERS', 2))
    PORT = int(os.getenv('PORT', 80))

app = Sanic("metrics-exporter-webserver")
app.config.FALLBACK_ERROR_FORMAT = "json"

def increment_metric(ctx, metric, labels, value=1):
    if labels not in ctx.metrics[metric]['metrics'].keys():
        ctx.metrics[metric]['metrics'][labels] = value
        return

    ctx.metrics[metric]['metrics'][labels] += value

'''
    Metrics bootstrap
'''
def fill_metric(mp_manager, ctx, metric_name, metric_help, metric_type, add_values=True):
    ctx.metrics[metric_name] = mp_manager.dict()
    ctx.metrics[metric_name]['help'] = metric_help
    ctx.metrics[metric_name]['type'] = metric_type
    if add_values:
        ctx.metrics[metric_name]['metrics'] = mp_manager.dict()

@app.main_process_start
async def add_metrics(app, _):
    mp_manager = Manager()

    app.shared_ctx.metrics = mp_manager.dict()
    fill_metric(mp_manager, app.shared_ctx, 'server_requests_total', "Total requests made to the server", "counter")
    fill_metric(mp_manager, app.shared_ctx, 'server_exporter_requests_total', "Total requests made to exporters", "counter")
    fill_metric(mp_manager, app.shared_ctx, 'server_exporter_seconds_total', "Total time spent handling exporters", "counter")
    fill_metric(mp_manager, app.shared_ctx, 'server_uptime_seconds_total', "Server uptime, in seconds", "counter", False)

    app.shared_ctx.metrics['server_uptime_seconds_total']['started'] = time.time()
    app.shared_ctx.metrics['server_uptime_seconds_total']['value'] = 0

'''
    Middleware for server metrics
'''
@app.middleware("request")
async def middleware_request(request):
    request.ctx.debug_request = False
    if request.args.get('debug') is not None:
        request.ctx.debug_request = True

    request.ctx.request_started_at = time.perf_counter()

@app.middleware("response")
async def middleware_response(request, response):
    increment_metric(request.app.shared_ctx, 'server_requests_total', f'status="{response.status}"')

    if not request.path.startswith('/metrics/'):
        return
        
    if response.status == 200 or response.status > 499:
        time_taken = time.perf_counter() - request.ctx.request_started_at

        increment_metric(request.app.shared_ctx, 'server_exporter_requests_total', f'path="{request.path}",status="{response.status}"')
        increment_metric(request.app.shared_ctx, 'server_exporter_seconds_total', f'path="{request.path}"', time_taken)

'''
    Route for web-server metrics
'''
@app.get("/metrics")
async def route_metrics(request):
    request.app.shared_ctx.metrics['server_uptime_seconds_total']['value'] = time.time() - app.shared_ctx.metrics['server_uptime_seconds_total']['started']

    blob = []

    for metric_name in request.app.shared_ctx.metrics.keys():
        blob.append(f"# HELP {metric_name} {request.app.shared_ctx.metrics[metric_name]['help']}")
        blob.append(f"# TYPE {metric_name} {request.app.shared_ctx.metrics[metric_name]['type']}")

        if 'value' in request.app.shared_ctx.metrics[metric_name].keys():
            blob.append(f"{metric_name} {request.app.shared_ctx.metrics[metric_name]['value']}")
            continue

        for labels, value in request.app.shared_ctx.metrics[metric_name]['metrics'].items():
            blob.append(f"{metric_name}{{{labels}}} {value}")

    blob.append("\n")

    return text("\n".join(blob))

'''
    Route for exporter metrics

    Optional query string parameters are mapped to exporter arguments
    ie. ?target=rack-sw01 becomes --target rack-sw01 - use with caution
'''
def param_valid(what):
    if re.match(r'^[a-zA-Z0-9\-_\.\,\:]+$', what) is None:
        return False

    return True

@app.get("/metrics/<exporter:str>")
async def route_metrics_exporter(request, exporter):
    arguments = []

    for pair in request.query_args:
        if not param_valid(pair[0]) or not param_valid(pair[1]):
            continue

        if pair[0] == 'debug':
            continue # intended for the web server

        arguments.append(pair[0])
        if pair[1] == "":
            continue

        arguments.append(pair[1])

    metrics_filename = f"/tmp/.metrics_{request.id}"

    proc = await asyncio.create_subprocess_shell(
        f"./metrics --exporter {exporter} --output-filename {metrics_filename} {' '.join(arguments)}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    http_status = 200
    process_output = {
        'returncode': 255,
        'stdout': '',
        'stderr': '',
        'metrics_filename': metrics_filename,
        'metrics': ''
    }

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=59
        )

        process_output['returncode'] = proc.returncode
        process_output['stdout'] = stdout.decode()
        process_output['stderr'] = stderr.decode()
    except asyncio.exceptions.TimeoutError:
        process_output['stderr'] = 'Killed: Timed out'

        try:
            proc.kill()
        except:
            pass

    try:
        with open(metrics_filename, "r") as data:
            process_output['metrics'] = data.read()
        
        os.remove(metrics_filename)
    except:
        pass

    if proc.returncode == 255:
        http_status = 404
        response = process_output['stdout']
    elif proc.returncode > 0:
        http_status = 500
        response = process_output['stderr']
    else:
        response = process_output['metrics']

    if request.ctx.debug_request:
        return json(process_output, status=http_status)

    return text(response, status=http_status)

if __name__ == "__main__":
    app.run(workers=Environment.WORKERS, host="0.0.0.0", port=Environment.PORT)
