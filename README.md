# metrics

My personal Pushgateway-capable metrics exporter wrapper. Includes a HTTP server for pull exposition.

**Usage via the built-in web server is recommended.**   

Cisco exporter included as an example.

## Installation

Exporters have different requirements, it is recommended to build an image with requirements for exporters you'd like to run.

### Docker image

Dockerfile is provided for setting up images for use with the built in web server. Installing pip requirements for exporters at build time can be done via the `EXPORTERS` build-arg, for example: `docker build --build-arg="EXPORTERS=dummy,cisco" .` would build the image and a helper script would install relevant packages from each exporters `requirements.txt`.

### Quick local installation

Python >= 3.8 is required

1. `python3 -m venv venv`
2. `source venv/bin/activate`
3. `pip install --upgrade pip`
4. `pip install -r requirements.txt`

For each exporter you intend on running: *
- `pip install -r exporters/EXPORTER/requirements.txt`   
example: `pip install -r exporters/cisco/requirements.txt`   

\* *different exporters may have different steps required for them to run*

## Usage (web server)

HTTP server can be started via `server.py`. The web server launches exporters as a sub process and collects their metrics through a temporary file, which ensures that the metrics are not polluted by output from print statements, etc.

```
 web server (pull) model
┌────────┐           ┌────────────┐
│ client ├──────────►│ web server │
└────────┘           └─┬───────▲──┘
                       │   ┌───┴────────────────┐
                       │   │ stdout, stderr     │
                       │   │ file (per request) │
                       │   └───┬────────────────┘
                    ┌┬─▼───────┴──┬┐
                    ││ exporters  ││
                    └┴────────────┴┘

 pushgateway (push) model
 ┌───────────┐       ┌────────────┐       ┌─────────────┐
 │ ./metrics ├───────►  exporter  ├───────► Pushgateway │
 └───────────┘       └────────────┘       └─────────────┘
```

Using the subprocess model allows the exporter process to "do whatever it wants", including spawning daemonic child processes for maximum parallel processing.

Environment variables:

| variable | description                | default |
| -------- | -------------------------- | ------- |
| WORKERS  | Number of worker processes | 2       |
| PORT     | HTTP port                  | 80      |

The API is as follows:

#### GET /metrics
*return web server metrics*

| metric                         | description                                                                       | type    | example value |
| ------------------------------ | --------------------------------------------------------------------------------- | ------- | ------------- |
| server_requests_total          | Total requests made to the server, grouped by HTTP status code                    | counter | 5             |
| server_exporter_requests_total | Total requests made to exporters, grouped by exporter (path) and HTTP status code | counter | 5             |
| server_exporter_seconds_total  | Total time spent handling exporters, in seconds, grouped by exporter (path)       | counter | 2.152         |
| server_uptime_seconds_total    | Server uptime, in seconds                                                         | counter | 152           |

#### GET /metrics/`exporter`
*execute exporter `exporter` and return its metrics*

Exporter execution is the same as if it was run through `./metrics`. Exporter args can be provided as query string parameters, for example: `GET /metrics/cisco?--target=core-sw01` would convert the query to equivalent of `./metrics --exporter cisco --target core-sw01` \*

\* *I did not bother accounting for spaces in argument values*

If the `debug` query parameter is provided, the response model changes from the exported metrics into a JSON object as below:

```
{
    'returncode': 1,
    'stdout': 'stdout of the process',
    'stderr': 'stderr of the process',
    'metrics-filename': 'file name intended for metrics',
    'metrics': 'metrics exported over provided file'
}
```

\* *returncode is the exit status of the process*

## Usage (exporters)

`./metrics --exporter EXPORTER [argument1, argument2...]`   

Where `EXPORTER` is the name of the exporter intended to be run. All optional arguments or arguments not listed in `-h` will be passed to the exporter.   

```
  -h, --help            show help message and exit
  --exporter NAME       Run metrics by exporter name
  --pushgateway-address HOST:PORT
                        Pushgateway address in host:port format
  --no-print            Do not print metrics to stdout
  --debug               Turn on debug mode, will be passed to exporter as a constructor argument
```

Example:
```
# ./metrics --exporter dummy
# HELP execution_seconds Summary of time spent executing something
# TYPE execution_seconds summary
execution_seconds_count{function="DummyExporter.my_custom_task"} 1.0
execution_seconds_sum{function="DummyExporter.my_custom_task"} 0.55
execution_seconds_count{function="DummyExporter.observed_function"} 1.0
execution_seconds_sum{function="DummyExporter.observed_function"} 1.101
# HELP dummy_gauge A dummy metric, means nothing.
# TYPE dummy_gauge gauge
dummy_gauge 0.0
# HELP dummy_counter_total A dummy metric, means nothing.
# TYPE dummy_counter_total counter
dummy_counter_total{dummy_label="dummy_label_value"} 1.0
# HELP generic_timer_seconds_total Value of generic timer
# TYPE generic_timer_seconds_total counter
generic_timer_seconds_total 0.25
```

# Building exporters

Please review `exporters/exporter.py` and `exporters/dummy.py`.   

The wrapper assumes the following:
1. An exporter can be its own file in `exporters/*.py` or can be in its own sub-directory such as `exporters/my_exporter/my_exporter.py`.
2. All arguments not listed in the help text are passed to the exporter.
3. All exporters must inherit the base `Exporter` class.
4. Metrics collector specific to the exporter is available inside the exporter under `self.metrics`. Full documentation of the module here: https://github.com/prometheus/client_python

Assuming that all the above is followed, exposition of metrics and push to pushgateway will be handled automatically.   

## A word of warning for those that intend on going fast

The metrics collector is not thread-safe. You are welcome to do all the workload in parallel, but ensure the update of metric values is done in the main thread, preferably inside `gather_metrics()`
