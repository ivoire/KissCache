# -*- coding: utf-8 -*-
# vim: set ts=4

# Copyright 2018 Rémi Duraffort
# This file is part of KissCache.
#
# KissCache is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KissCache is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with KissCache.  If not, see <http://www.gnu.org/licenses/>

# fail after 10 minutes
DOWNLOAD_TIMEOUT = 10 * 60

# base directory
DOWNLOAD_PATH = "/var/cache/kiss-cache"

# Download 1kB by 1kB
DOWNLOAD_CHUNK_SIZE = 1024

# By default, keep the resources for 1 day
DEFAULT_TTL = "1d"

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

# Quota
RESOURCE_QUOTA = 200 * 1024 * 1024
