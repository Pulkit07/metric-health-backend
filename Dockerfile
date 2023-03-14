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
    && apt-get install -y --no-install-recommends libpq-dev nginx\
    && rm -rf /var/lib/apt/lists/*

COPY nginx/prod/nginx.conf /etc/nginx/sites-available/default

# install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

STOPSIGNAL SIGTERM
EXPOSE 80

CMD ["./start-server.sh"]
