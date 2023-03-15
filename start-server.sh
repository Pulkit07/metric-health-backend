#!/usr/bin/env bash
# start-server.sh
(gunicorn core.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000) &
nginx -g "daemon off;"