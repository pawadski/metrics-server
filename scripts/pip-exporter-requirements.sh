#!/bin/bash
IFS=','

for exporter in $1; do
    echo "[$0] installing for: $exporter"
    if [ ! -f "/app/exporters/$exporter/requirements.txt" ]; then
        continue
    fi

    python3 -m pip install -r /app/exporters/$exporter/requirements.txt
done