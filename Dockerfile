# base image for Django python
FROM python:3.9-slim

RUN mkdir -p /usr/src/app

# set work directory
WORKDIR /app

# copy project
COPY . /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# install dependencies
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel
RUN pip install -r requirements.txt


EXPOSE 80