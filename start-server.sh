#!/usr/bin/env bash
# start-server.sh
(daphne core.asgi:application --bind 0.0.0.0 --port 5000) &
nginx -g "daemon off;"