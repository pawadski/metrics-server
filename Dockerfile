FROM ubuntu:focal

ARG EXPORTERS=dummy

RUN apt-get update && apt-get -y install python3 python3-pip
RUN python3 -m pip install --upgrade pip 

RUN mkdir -p /app

COPY ./ /app

WORKDIR /app

RUN python3 -m pip install -r requirements.txt && \
    bash /app/scripts/pip-exporter-requirements.sh ${EXPORTERS}

ENTRYPOINT ["python3", "-u", "server.py"]
