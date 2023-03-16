#!/usr/bin/env bash
# start-server.sh
python manage.py migrate
python -m celery -A core worker -l info &
(gunicorn core.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000) &
nginx -g "daemon off;"