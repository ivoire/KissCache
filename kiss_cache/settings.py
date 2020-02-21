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
