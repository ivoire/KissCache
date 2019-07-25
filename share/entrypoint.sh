#!/bin/sh

[ -n "$1" ] && exec "$@"

python3 manage.py migrate --noinput
exec gunicorn3 --log-level debug --bind 0.0.0.0:80 --threads 10 --workers 4 --worker-tmp-dir /dev/shm website.wsgi
