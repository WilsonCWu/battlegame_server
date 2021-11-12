# syntax=docker/dockerfile:1
FROM python:3
ENV COMPOSE_CONVERT_WINDOWS_PATHS=1
ENV PYTHONUNBUFFERED=1

# Set up venv by setting the venv folder as PATH
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Apt-get updates/upgrades that are necessary to install requirements
RUN apt-get update
RUN apt-get upgrade --assume-yes
RUN apt-get install --assume-yes git
RUN apt-get install --assume-yes libpq-dev

# Prepare actual server
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
ADD . /code/