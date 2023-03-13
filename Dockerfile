# base image for Django python
FROM python:3.9-alpine

RUN mkdir -p /usr/src/app

# set work directory
WORKDIR /app

# copy project
COPY . /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev

# install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt


EXPOSE 80