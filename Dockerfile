# base image for Django python
FROM python:3.8

RUN mkdir -p /usr/src/app

# set work directory
WORKDIR /usr/src/app

# copy project
COPY . /usr/src/app/

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt


EXPOSE 8000