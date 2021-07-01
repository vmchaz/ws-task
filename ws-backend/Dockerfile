FROM python:3.8-slim-buster as ws_backend

COPY . /opt/ws_backend

# install dependencies
RUN apt-get -y update
RUN apt-get -y install gcc
RUN apt-get -y install libpq-dev
#RUN apt-get -y install gunicorn
RUN pip3 install --upgrade pip
RUN pip3 install -r /opt/ws_backend/requirements.txt
RUN pwd
RUN ls -la
CMD ["gunicorn", "backend:app", "--bind", "0.0.0.0:5000", "--workers=4", "--chdir=/opt/ws_backend"]
