#!/bin/sh
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

set -e

[ -n "$1" ] && exec "$@"

#######################
# wait for postgresql #
#######################
check_pgsql() {
    python3 manage.py shell -c "import sys
from django.db import connections
try:
  connections['default'].cursor()
except Exception:
  sys.exit(1)
sys.exit(0)"
}

wait_postgresql() {
    until check_pgsql
    do
        printf "."
        sleep 1
    done
}


###########################
# wait for the migrations #
###########################
check_initial_migrations() {
    python3 manage.py shell -c "import sys
import django
from django.db import connections
try:
    connections['default'].cursor().execute('SELECT * from django_migrations')
except django.db.utils.Error:
    sys.exit(1)
sys.exit(0)"
}

check_migrations() {
    migrations=$(python3 manage.py showmigrations --plan)
    if [ "$?" != "0" ]
    then
        return 1
    fi
    return $(echo "$migrations" | grep -c "\\[ \\]")
}

wait_migration() {
    # Check that the django_migrations table exist before calling 'showmigrations'.
    # In fact, 'showmigrations' will create the table if it's missing. But if
    # two processes try to create the table at the same time, the last to
    # commit will crash.
    until check_initial_migrations
    do
        echo "."
        sleep 1
    done
    # The table exist, calling 'showmigrations' is now idempotent.
    until check_migrations
    do
        echo "."
        sleep 1
    done
}

if [ "$SERVICE" = "nginx" ]
then
  exec nginx -c /etc/nginx/kiss-cache.conf -g 'daemon off;'
elif [ "$SERVICE" = "celery-worker" ]
then
  echo "Waiting for postgresql"
  wait_postgresql
  echo "done"
  echo ""
  echo "Waiting for migrations"
  wait_migration
  echo "done"
  echo ""

  if [ "$CELERY_CONCURRENCY" != "" ]
  then
    CELERY_CONCURRENCY="--concurrency $CELERY_CONCURRENCY"
  fi
  exec python3 -m celery -A website worker $CELERY_CONCURRENCY --loglevel=INFO
elif [ "$SERVICE" = "celery-beat" ]
then
  exec python3 -m celery -A website beat --loglevel=INFO --pidfile= -s /var/cache/kiss-cache/celerybeat-schedule
elif [ "$SERVICE" = "gunicorn" ]
then
  echo "Waiting for postgresql"
  wait_postgresql
  echo "done"
  echo ""
  echo "Applying migrations"
  python3 manage.py migrate --noinput || FAILED=1
  if [ "$FAILED" = "1" ]
  then
    echo "Can not apply migrations"
    echo "Waiting for migrations"
    wait_migration
  fi
  echo "done"
  echo ""

  GUNICORN_THREADS=${GUNICORN_THREADS:-10}
  GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
  echo "Starting gunicorn with workers=$GUNICORN_WORKERS and threads=$GUNICORN_THREADS"
  exec gunicorn3 --log-level debug --log-file - --access-logfile - --bind 0.0.0.0:80 --threads "$GUNICORN_THREADS" --workers "$GUNICORN_WORKERS" --worker-tmp-dir /dev/shm website.wsgi
fi
