# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

# fail after 10 minutes
DOWNLOAD_TIMEOUT = 10 * 60
# See https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html
DOWNLOAD_RETRY = 15
# A backoff factor to apply between attempts after the second try (most errors
# are resolved immediately by a second try without a delay). urllib3 will sleep
# for:
#    {backoff factor} * (2 ** ({number of total retries} - 1))
# seconds. If the backoff_factor is 0.1, then sleep() will sleep for [0.0s,
# 0.2s, 0.4s, …] between retries.
DOWNLOAD_BACKOFF_FACTOR = 0.1

# base directory
DOWNLOAD_PATH = "/var/cache/kiss-cache"

# Download 1kB by 1kB
DOWNLOAD_CHUNK_SIZE = 1024

# By default, keep the resources for 10 days
DEFAULT_TTL = "10d"

# When this file exists, a call to /api/v1/health/ will return 503
# Allow to implement graceful shutdown and interact with load balancers
SHUTDOWN_PATH = "/var/lib/kiss-cache/shutdown"

# Celery specific configuration
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_CONCURRENCY = 10
CELERY_WORKER_SEND_TASK_EVENTS = True

# Setup the scheduler
CELERY_BEAT_SCHEDULE = {
    "expire-every-hour": {"task": "kiss_cache.tasks.expire", "schedule": 60 * 60}
}
CELERY_BEAT_MAX_LOOP_INTERVAL = 30 * 60

# List of networks that can fetch resources
# By default the instance is fully open
ALLOWED_NETWORKS = []

# Default quota of 2G
RESOURCE_QUOTA = 2 * 1024 * 1024 * 1024
