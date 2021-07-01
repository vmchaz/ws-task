FROM python:3.8-slim-buster as ws_engine

COPY . /opt/ws_engine

# install dependencies
RUN apt-get -y update
RUN apt-get -y install gcc
RUN apt-get -y install libpq-dev
RUN pip3 install --upgrade pip
RUN pip3 install -r /opt/ws_engine/requirements.txt
CMD ["python3", "/opt/ws_engine/engine.py"]
