# fail after 10 minutes
DOWNLOAD_TIMEOUT = 10 * 60

# base directory
DOWNLOAD_PATH = "/var/cache/kiss-cache"

DOWNLOAD_CHUNK_SIZE = 1024

DEFAULT_TTL = "1d"

# Celery specific configuration
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_CONCURRENCY = 10
CELERY_WORKER_SEND_TASK_EVENTS = True

# Setup the scheduler
CELERY_BEAT_SCHEDULE = {
    "expire-every-hour": {"task": "kiss_cache.tasks.expire", "schedule": 600.0}
}
CELERY_BEAT_MAX_LOOP_INTERVAL = 300
